import paho.mqtt.client as mqtt
import time

BROKER = "13.63.71.56"
PORT = 1883
TOPIC = "test/connectivity"

client = mqtt.Client("PiSimpleTest")

try:
    client.connect(BROKER, PORT)
    print("Connected successfully!")
    message = "Hello AWS, the Raspberry Pi is officially online!"
    client.publish(TOPIC, message)

    time.sleep(1) 
    client.disconnect()

except Exception as e:
    print(f"Connection failed: {e}")