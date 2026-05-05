import socket
import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Bluetooth (STM32 RN-42)
TARGET_MAC = "00:14:03:05:5A:0A"  # <-- Change to your RN-42 MAC Address
BT_PORT = 1

# AWS MQTT
AWS_BROKER = "YOUR_AWS_PUBLIC_IP_HERE" # <-- Change to your AWS IP
MQTT_PORT = 1883
MQTT_TOPIC = "cybergarden/sensors"

# ==========================================
# 2. MQTT SETUP
# ==========================================
mqtt_client = mqtt.Client("PiEdgeGateway")

print(f"☁️ Connecting to AWS Broker at {AWS_BROKER}...")
try:
    mqtt_client.connect(AWS_BROKER, MQTT_PORT)
    mqtt_client.loop_start()  # Starts a background thread to manage the network
    print("✅ AWS Connected!")
except Exception as e:
    print(f"❌ AWS Connection failed: {e}")
    exit()

# ==========================================
# 3. DATA VALIDATION FUNCTION
# ==========================================
def validate_and_format(raw_string):
    """
    Takes the raw string from STM32, verifies it is valid JSON, 
    checks for required keys, and adds a cloud-ready timestamp.
    """
    try:
        # 1. Try to parse the string into a Python dictionary
        data = json.loads(raw_string)
        
        # 2. Verify the STM32 sent the correct required keys
        required_keys = ["temp", "humidity", "water_level"]
        for key in required_keys:
            if key not in data:
                print(f"⚠️ Validation Failed: Missing '{key}' in payload.")
                return None
                
        # 3. Add the exact Edge timestamp (Best Practice!)
        data["timestamp"] = datetime.now().isoformat()
        
        # 4. Return the cleaned, verified JSON string ready for AWS
        return json.dumps(data)
        
    except json.JSONDecodeError:
        print(f"🗑️ Invalid JSON received (Garbage data): {raw_string}")
        return None

# ==========================================
# 4. BLUETOOTH LOOP
# ==========================================
def run_gateway():
    print(f"🔌 Connecting to STM32 Bluetooth ({TARGET_MAC})...")
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    
    try:
        sock.connect((TARGET_MAC, BT_PORT))
        print("✅ STM32 Connected! Listening for data...\n")
        
        buffer = "" # This holds partial messages
        
        while True:
            # Receive chunk of data from Bluetooth
            chunk = sock.recv(1024)
            if not chunk:
                print("⚠️ STM32 disconnected.")
                break
                
            # Add new chunk to our text buffer
            buffer += chunk.decode('utf-8')
            
            # Process complete lines (split by newline)
            while '\n' in buffer:
                # Split the buffer at the first newline
                line, buffer = buffer.split('\n', 1)
                line = line.strip() # Remove extra spaces/carriage returns
                
                if line:
                    print(f"\n📥 Received from STM32: {line}")
                    
                    # Pass the complete line to our validation function
                    aws_payload = validate_and_format(line)
                    
                    # If validation passed, send to AWS!
                    if aws_payload:
                        result = mqtt_client.publish(MQTT_TOPIC, aws_payload)
                        if result[0] == 0:
                            print(f"📤 Forwarded to AWS: {aws_payload}")
                        else:
                            print("❌ Failed to forward to AWS (Network issue).")

    except ConnectionRefusedError:
        print("❌ Bluetooth connection refused. Is the RN-42 paired and powered?")
    except Exception as e:
        print(f"❌ Gateway Error: {e}")
    finally:
        sock.close()

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    try:
        while True:
            run_gateway()
            print("🔄 Retrying Bluetooth connection in 5 seconds...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🚪 Shutting down Edge Gateway.")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()