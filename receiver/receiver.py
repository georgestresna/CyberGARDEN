import json
import paho.mqtt.client as mqtt

###
DATA_FILE = "/db/data.json"
BROKER = "mosquitto"
PORT = 1883
TOPIC = "cybergarden/sensors"
###

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    data = json.loads(payload)
    
    try:
        with open(DATA_FILE, "r") as f:
            db_list = json.load(f)
        db_list.append(data)
        with open(DATA_FILE, "w") as f:
            json.dump(db_list, f, indent=4)
    except Exception as e:
        print(f"Error writing to DB: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "CybergardenReceiver")
client.on_message = on_message

print("🎧 Receiver Container listening for STM32 data...")
client.connect(BROKER, PORT)
client.subscribe(TOPIC)

client.loop_forever()