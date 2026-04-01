# from fastapi import FastAPI, Request
import json
import paho.mqtt.client as mqtt
# import os

# app = FastAPI()

###
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
# PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
# DATA_FILE = os.path.join(PROJECT_ROOT, "data.json")
DATA_FILE = "/db/data.json"
###

###
BROKER = "mosquitto"
PORT = 1883
TOPIC = "cybergarden/sensors"
###

# @app.post("/")
# async def receive_stm32_data(request: Request):
#     new_data = await request.json()
    
#     with open(DATA_FILE, "r") as file:
#         db = json.load(file)
#     db.append(new_data)
#     # if len(db) > 10:
#     #     db.pop(0)
        
#     with open(DATA_FILE, "w") as file:
#         json.dump(db, file, indent=4)
        
#     # Blackbox logic
#     if new_data.get("water_level", 100) < 20:
#         return {"status": "saved", "command": "OPEN_VALVE"}
#     else:
#         return {"status": "saved", "command": "STANDBY"}

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    data = json.loads(payload)
    
    # print(data)
    try:
        with open("/db/data.json", "r") as f:
            db_list = json.load(f)
        db_list.append(data)
        with open("/db/data.json", "w") as f:
            f.write(json.dump(db_list, f))
    except Exception as e:
        print(f"❌ Error writing to DB: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "CybergardenReceiver")
client.on_message = on_message

print("🎧 Receiver Container listening for STM32 data...")
client.connect(BROKER, PORT)
client.subscribe(TOPIC)

client.loop_forever()