import time
import random
# import requests
import paho.mqtt.client as mqtt
import json


#####
BROKER = "mosquitto"
PORT = 1883
TOPIC = "cybergarden/sensors"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "MockSTM32")
client.connect(BROKER, PORT)
#####

# BRAIN_URL = "http://receiver:8001/"

time.sleep(5)
print("Started serre databus")

while True:

    payload = {
        "temp": random.randint(15, 30),
        "humidity": random.randint(30, 60),
        "water_level": random.randint(5, 100)
    }

    payload = json.dumps(payload)
    client.publish(TOPIC, payload)
    print("     [~] Published data to Musquitto")
    
    # try:
    #     print(f"    [~] Sending POST request")
    #     response = requests.post(BRAIN_URL, json=payload)
    #     reply = response.json()
    #     print(f"    [~] Response: {reply}")
        
    # except requests.exceptions.RequestException as e:
    #     print(f"[!] Exception reached")
        
    time.sleep(10)