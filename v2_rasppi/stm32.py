import paho.mqtt.client as mqtt
import time
import json
import random
import datetime


BROKER = "13.63.71.56"
PORT = 1883
TOPIC = "cybergarden/sensors"

client = mqtt.Client("PiMockSender")
# client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "MockSTM32") 

def try_connection():
    try:
        client.connect(BROKER, PORT)
        print("Connected successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit()


try_connection()
print("📡 Starting to send mock data. Press Ctrl+C to stop.")
try:
    while True:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "temp": round(random.uniform(20.0, 26.0), 1),
            "humidity": round(random.uniform(45.0, 65.0), 1),
            "water_level": random.randint(50, 100),
            "pump_state": 0
        }
        
        json_payload = json.dumps(payload)
        
        # Fire it up to the AWS broker
        result = client.publish(TOPIC, json_payload)

        status = result[0]
        if not status:
            print("Data created & published")
        else:
            print("Data created but couldn t be published | trying to reconnect before sending next batch")
            try_connection()

        time.sleep(5)

except KeyboardInterrupt:
    print("\n🚪 Stopping script and disconnecting.")
    client.disconnect()