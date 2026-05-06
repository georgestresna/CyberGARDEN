import time
import random
import paho.mqtt.client as mqtt
import json


#####
BROKER = "mosquitto"
PORT = 1883
TOPIC_DATA = "cybergarden/sensors"
TOPIC_COMMANDS = "cybergarden/commands/pump"
#####

#####

# The physical state of our fake hardware (0 = OFF, 1 = ON)
current_pump_state = 0


# --- 1. THE EARS (Listening for Web Commands) ---
def on_message(client, userdata, msg):
    global current_pump_state
    try:
        command = msg.payload.decode()
        print(f"\n📥 [COMMAND RECEIVED]: The Web Server said '{command}'")
        
        if command == "1":
            current_pump_state = 1
            print("💧 Hardware Action: CLICK! Pump turned ON.")
        elif command == "0":
            current_pump_state = 0
            print("🛑 Hardware Action: CLICK! Pump turned OFF.")
            
    except Exception as e:
        print(f"❌ Error processing command: {e}")

# --- 2. SETUP MQTT CLIENT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "MockSTM32")
client.on_message = on_message

client.connect(BROKER, PORT)

time.sleep(5)
print("Started serre databus")


client.subscribe(TOPIC_COMMANDS)
# Start a background thread to listen for incoming messages
client.loop_start()


### the mouth
try:
    while True:
        # Generate fake sensor data, but include our REAL pump state
        data = {
            "temp": round(random.uniform(20.0, 30.0), 1),
            "humidity": random.randint(40, 60),
            "water_level": random.randint(10, 90),
            "pump_state": current_pump_state 
        }
        
        # Publish it to Mosquitto
        client.publish(TOPIC_DATA, json.dumps(data))
        print(f"📡 [DATA SENT]: {data}")
        
        # Wait 5 seconds before checking the sensors again
        time.sleep(10)
        
except KeyboardInterrupt:
    print("Shutting down STM32...")
    client.loop_stop()
    client.disconnect()