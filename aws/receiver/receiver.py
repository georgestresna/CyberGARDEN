import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime
from pymongo import MongoClient

# ==========================================
# 1. CONFIGURATION FROM ENVIRONMENT
# ==========================================
# Grabbing settings from docker-compose, with safe fallbacks
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
BROKER = os.getenv("MQTT_HOST", "mosquitto")
PORT = 1883
TOPIC = "cybergarden/sensors"

# ==========================================
# 2. DATABASE CONNECTION
# ==========================================
print(f"🔌 Connecting to MongoDB at {MONGO_URL}...")
try:
    mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = mongo_client.cybergarden
    # Tells MongoDB to automatically delete documents 30 days (2592000 seconds) after their 'timestamp'
    db.sensors.create_index("timestamp", expireAfterSeconds=2592000)
    # Trigger a quick ping to ensure it's actually connected before continuing
    mongo_client.admin.command('ping') 
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(f"❌ FATAL: Could not connect to MongoDB: {e}")
    exit(1)

# ==========================================
# 3. MQTT CALLBACK (What happens when data arrives)
# ==========================================
def on_message(client, userdata, msg):
    try:
        # Decode the byte string into text, then parse the JSON
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        # Check if the Edge Gateway (Pi) already added a timestamp. 
        # If not, add a server-side timestamp.
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
            
        # Insert the data into the 'sensors' collection in MongoDB
        db.sensors.insert_one(data)
        print(f"💾 Saved to DB: {data}")
        
    except json.JSONDecodeError:
        print(f"⚠️ Ignored non-JSON message: {msg.payload}")
    except Exception as e:
        print(f"❌ Error writing to DB: {e}")

# ==========================================
# 4. MQTT SETUP & LOOP
# ==========================================
# Using the Version 2 syntax since we are doing a fresh install in Docker
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "CybergardenReceiver")
mqtt_client.on_message = on_message

print(f"🎧 Connecting to MQTT Broker at {BROKER}...")
try:
    mqtt_client.connect(BROKER, PORT)
    mqtt_client.subscribe(TOPIC)
    print("✅ Connected to Mosquitto! Listening for STM32 data...")
    
    # Block and run forever
    mqtt_client.loop_forever()
    
except Exception as e:
    print(f"❌ Failed to connect to MQTT: {e}")