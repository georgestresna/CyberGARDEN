import time
import random
import paho.mqtt.client as mqtt
import json


#####
BROKER = "mosquitto"
PORT = 1883
TOPIC = "cybergarden/sensors"
#####
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "MockSTM32")
client.connect(BROKER, PORT)
#####


time.sleep(5)
print("Started serre databus")

#dummy data for the stm32
while True:

    payload = {
        "temp": random.randint(15, 30),
        "humidity": random.randint(30, 60),
        "water_level": random.randint(5, 100)
    }

    payload = json.dumps(payload)
    client.publish(TOPIC, payload)
    print("     [~] Published data to Musquitto")
        
    time.sleep(10)