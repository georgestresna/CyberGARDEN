import time
import random
import requests

BRAIN_URL = "http://receiver:8001/"

time.sleep(5)
print("Started serre databus")

while True:

    payload = {
        "temp": random.randint(15, 30),
        "humidity": random.randint(30, 60),
        "water_level": random.randint(5, 100)
    }
    
    try:
        print(f"    [~] Sending POST request")
        response = requests.post(BRAIN_URL, json=payload)
        reply = response.json()
        print(f"    [~] Response: {reply}")
        
    except requests.exceptions.RequestException as e:
        print(f"[!] Exception reached")
        
    time.sleep(10)