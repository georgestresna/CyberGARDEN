import socket
import time
import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
TARGET_MAC = "00:06:66:6E:10:B8"  # RN-42 MAC
BT_PORT = 1

# Pull AWS IP from docker-compose environment variables
AWS_BROKER = os.getenv("AWS_BROKER", "127.0.0.1") 
MQTT_PORT = 1883
MQTT_TOPIC = "cybergarden/sensors"

# ==========================================
# 2. MQTT SETUP
# ==========================================
# Note: Using CallbackAPIVersion.VERSION2 for the latest paho-mqtt support
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "PiEdgeGateway")

print(f"☁️ Connecting to AWS Broker at {AWS_BROKER}...")
try:
    mqtt_client.connect(AWS_BROKER, MQTT_PORT)
    mqtt_client.loop_start() 
    print("✅ AWS Connected!")
except Exception as e:
    print(f"❌ AWS Connection failed: {e}")
    exit()

def validate_and_format(raw_string):
    try:
        data = json.loads(raw_string)
        required_keys = ["temperature", "humidite", "lumiere", "distance"]
        for key in required_keys:
            if key not in data:
                print(f"⚠️ Validation Failed: Missing '{key}' in payload.")
                return None
        data["timestamp"] = datetime.now().isoformat()
        return json.dumps(data)
    except json.JSONDecodeError:
        print(f"🗑️ Invalid JSON received: {raw_string}")
        return None

def run_gateway():
    print(f"🔌 Connecting to STM32 Bluetooth ({TARGET_MAC})...")
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        sock.connect((TARGET_MAC, BT_PORT))
        print("✅ STM32 Connected! Listening for data...\n")
        
        buffer = "" 
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                print("⚠️ STM32 disconnected.")
                break
                
            buffer += chunk.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                
                if line:
                    print(f"📥 STM32: {line}")
                    aws_payload = validate_and_format(line)
                    if aws_payload:
                        result = mqtt_client.publish(MQTT_TOPIC, aws_payload)
                        if result.rc == 0:
                            print(f"📤 AWS: {aws_payload}")
                        else:
                            print("❌ Failed to forward to AWS.")

    except ConnectionRefusedError:
        print("❌ Bluetooth connection refused. Is RN-42 paired/powered?")
    except Exception as e:
        print(f"❌ Gateway Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    try:
        while True:
            run_gateway()
            print("🔄 Retrying BT in 5 seconds...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🚪 Shutting down Edge Gateway.")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()