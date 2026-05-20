import socket
import time
import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta


# Bluetooth module static info
TARGET_MAC = "00:06:66:6E:10:B8" 
BT_PORT = 1 

AWS_BROKER = os.getenv("AWS_BROKER", "127.0.0.1") 
MQTT_PORT = 1883
MQTT_PUB_TOPIC = "cybergarden/sensors"
MQTT_SUB_TOPIC = "cybergarden/commands/#"

# Logic thresholds
HUMIDITY_THRESHOLD = 30.0   # Turn on if humidity drops below 30%
COOLDOWN_MINUTES = 10       # Wait 10 mins after watering before checking again

# Global State
bt_sock = None
auto_suspended_until = datetime.now()

def send_to_stm32(command_char):
    """Safely sends a character ('1' or '0') over Bluetooth to the STM32."""
    global bt_sock
    if bt_sock:
        try:
            # We add a newline character so the STM32 knows the command is complete
            msg = f"{command_char}\n"
            bt_sock.send(msg.encode('utf-8'))
            print(f"[*] Sent '{command_char}' to STM32.")
        except Exception as e:
            print(f"[!] Failed to send command to STM32: {e}")
    else:
        print("[!] Cannot send command. STM32 is not connected.")


def on_message(client, userdata, msg):
    """Fires instantly whenever you press the button on the Web Dashboard."""
    global auto_suspended_until
    
    command = msg.payload.decode('utf-8').strip()
    topic = msg.topic
    
    print(f"\n[*] AWS MANUAL COMMAND RECEIVED on {topic}: {command}")
    
    # --- 1. WATER PUMP COMMAND ---
    if topic == "cybergarden/commands/pump" and command == "1":
        # Send '1' to STM32 for the pump
        send_to_stm32("1")
        # Suspend automatic watering so they don't fight
        auto_suspended_until = datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)
        print(f"[*] Auto-watering suspended until {auto_suspended_until.strftime('%H:%M:%S')} to let water soak in.")
        
    # --- 2. VENTILATOR COMMAND ---
    elif topic == "cybergarden/commands/fan" and command == "1":
        # Send '2' to STM32 for the fan
        send_to_stm32("2")
        print("[*] Fan triggered for 5 seconds.")

# Setup MQTT
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "PiEdgeGateway")

mqtt_client.on_message = on_message

print(f"[*] Connecting to AWS Broker at {AWS_BROKER}...")
try:
    mqtt_client.connect(AWS_BROKER, MQTT_PORT)
    mqtt_client.subscribe(MQTT_SUB_TOPIC) # Start listening for the button!
    mqtt_client.loop_start() 
    print("[*] AWS Connected & Listening for commands!")
except Exception as e:
    print(f"[*] AWS Connection failed: {e}")
    exit()

def run_gateway():
    global bt_sock, auto_suspended_until
    
    print(f"[*] Connecting to STM32 Bluetooth ({TARGET_MAC})...")
    bt_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        bt_sock.connect((TARGET_MAC, BT_PORT))
        print("     [*] STM32 Connected! Listening for data...\n")
        
        buffer = "" 
        while True:
            #Listen for sensor data
            chunk = bt_sock.recv(1024)
            if not chunk:
                print("     [!] STM32 disconnected.")
                break
                
            buffer += chunk.decode('utf-8')
            
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                
                if line:
                    print(f"    [*] STM32 Sensor Data: {line}")
                    
                    #Process and forward data to AWS
                    try:
                        data = json.loads(line)
                        data["timestamp"] = datetime.now().isoformat()
                        aws_payload = json.dumps(data)
                        mqtt_client.publish(MQTT_PUB_TOPIC, aws_payload)
                        
                        #BRAIN Logic (Automation): Only check the soil if we aren't in a cooldown period
                        if datetime.now() > auto_suspended_until:
                            humidity = float(data.get("humidity", 100))
                            
                            if humidity < HUMIDITY_THRESHOLD:
                                print(f"     [*] AUTO: Soil is dry ({humidity}%). Triggering water pulse.")
                                send_to_stm32("1")
                                # Suspend auto-logic for 10 mins to let water sink into the dirt
                                auto_suspended_until = datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)
                                
                    except json.JSONDecodeError:
                        print("     [!] Invalid JSON received.")
                        
    except Exception as e:
        print(f"[!] Gateway Error: {e}")
    finally:
        if bt_sock:
            bt_sock.close()
            bt_sock = None

if __name__ == "__main__":
    try:
        while True:
            run_gateway()
            print("[!] Retrying Bluetooth in 5 seconds...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[!] Shutting down Edge Gateway.")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()