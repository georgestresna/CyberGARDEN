import socket
import time
import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime
from automation_logic import AutomationController


# Bluetooth module static info
TARGET_MAC = "00:06:66:6E:10:B8" 
BT_PORT = 1 

AWS_BROKER = os.getenv("AWS_BROKER", "127.0.0.1") 
MQTT_PORT = 1883
MQTT_PUB_TOPIC = "cybergarden/sensors"
MQTT_SUB_TOPIC = "cybergarden/commands/#"

automation = AutomationController(
    soil_threshold=35.0,
    air_humidity_threshold=75.0,
    temperature_threshold=28.0,
    watering_duration_seconds=5,
    cooldown_minutes=10,
    min_water_distance_cm=18.0
)

# Global State
bt_sock = None

def send_to_stm32(command_char):
    """Safely sends a command over Bluetooth to the STM32."""
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
    """
    Gère les commandes manuelles reçues depuis AWS / Dashboard.
    """
    command = msg.payload.decode('utf-8').strip()
    topic = msg.topic
    
    print(f"\n[*] AWS MANUAL COMMAND RECEIVED on {topic}: {command}")
    
    # Sécuriser la conversion en entier (0 ou 1)
    try:
        state = int(command)
    except ValueError:
        print("[!] Invalid command format.")
        return

    # --- 1. POMPE (ARROSAGE) ---
    if topic == "cybergarden/commands/pump":
        # Informer le cerveau de l'override
        automation.handle_manual_command("valve", state)
        
        # Envoyer la commande physique ("1" pour ON, "0" pour OFF)
        hardware_cmd = "1" if state == 1 else "0"
        send_to_stm32(hardware_cmd)
        print(f"[*] Manual Pump Override: {'ON' if state == 1 else 'OFF'}")

    # --- 2. VENTILATEUR ---
    elif topic == "cybergarden/commands/fan":
        # Informer le cerveau de l'override
        automation.handle_manual_command("fan", state)
        
        # Envoyer la commande physique ("F" pour ON, "f" pour OFF selon votre logique existante)
        hardware_cmd = "F" if state == 1 else "f"
        send_to_stm32(hardware_cmd)
        print(f"[*] Manual Fan Override: {'ON' if state == 1 else 'OFF'}")

        
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
    global bt_sock
    
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
                        commands = automation.process_sensor_data(data)
                        for command in commands:
                            print(f"     [AUTO] {command['reason']}")

                            if command["target"] == "valve":
                                if command["state"] == 1:
                                    send_to_stm32("1")
                                else:
                                    send_to_stm32("0")

                            elif command["target"] == "fan":
                                if command["state"] == 1:
                                    send_to_stm32("F")
                                else:
                                    send_to_stm32("f")

                            elif command["target"] == "alert":
                                print("     [ALERT] Water tank is probably empty.")
                                
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