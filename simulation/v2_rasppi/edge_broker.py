import paho.mqtt.client as mqtt
import time
import json
import random


BROKER = "51.21.162.115"
PORT = 1883
TOPIC_DATA = "cybergarden/sensors"
TOPIC_COMMANDS = "cybergarden/commands/pump"

current_pump_state = 0 
pump_turn_on_time = 0

MAX_PUMP_TIME_SECONDS = 120  
CRITICAL_MOISTURE_HIGH = 85  
CRITICAL_MOISTURE_LOW = 15   

# We simulate moisture independently so we can see it go up when the pump is on
simulated_moisture = 45 

# --- 3. THE EARS (Listening to AWS) ---
def on_message(client, userdata, msg):
    global current_pump_state, pump_turn_on_time, simulated_moisture
    command = msg.payload.decode()
    
    if command == "1":
        if simulated_moisture >= CRITICAL_MOISTURE_HIGH:
            print("🛑 EDGE OVERRIDE: Cloud said ON, but soil is too wet. Ignored.")
        else:
            current_pump_state = 1
            pump_turn_on_time = time.time()
            print("\n💧 AWS COMMAND RECEIVED: Pump turned ON (Timeout started).")
            
    elif command == "0":
        current_pump_state = 0
        print("\n🛑 AWS COMMAND RECEIVED: Pump turned OFF.")

# --- 4. SETUP MQTT CONNECTION ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "PiSmartMock")
client.on_message = on_message

print(f"🌱 Smart Edge Booting Up... Connecting to AWS at {BROKER}")
try:
    client.connect(BROKER, PORT)
    client.subscribe(TOPIC_COMMANDS)
    client.loop_start()
except Exception as e:
    print(f"❌ Could not connect to AWS: {e}")
    print("Check your AWS Security Groups (Port 1883) and internet connection.")
    exit()

# --- 5. THE WATCHDOG & DATA LOOP ---
try:
    while True:
        # 1. Simulate the physical environment
        simulated_temp = round(random.uniform(20.0, 30.0), 1)
        simulated_water_level = random.randint(10, 90) # Reservoir level
        
        if current_pump_state == 1:
            simulated_moisture += 2 # Moisture goes up if pump is running
        else:
            simulated_moisture -= 0.5 # Slowly dries out naturally
            
        # Keep moisture in realistic bounds (0-100)
        simulated_moisture = max(0, min(100, simulated_moisture))

        # 2. Safety Check 1: Timeout (Did the human leave it on?)
        if current_pump_state == 1:
            if (time.time() - pump_turn_on_time) > MAX_PUMP_TIME_SECONDS:
                print("⏱️ TIMEOUT: Auto-shutting off the pump to prevent flooding!")
                current_pump_state = 0

        # 3. Safety Check 2: Emergency Auto-Water (Did the human forget?)
        if simulated_moisture <= CRITICAL_MOISTURE_LOW and current_pump_state == 0:
            print("🚨 EMERGENCY: Soil is critically dry! Auto-watering started.")
            current_pump_state = 1
            pump_turn_on_time = time.time()

        # 4. Package and send the data to the Cloud
        data = {
            "temp": simulated_temp,
            "humidity": round(simulated_moisture, 1), # Reusing moisture for humidity in this mock
            "water_level": simulated_water_level,
            "pump_state": current_pump_state
        }
        
        client.publish(TOPIC_DATA, json.dumps(data))
        print(f"📡 Sent to AWS: {data}")
        
        time.sleep(5)
        
except KeyboardInterrupt:
    print("\nShutting down Smart Edge Simulator...")
    client.loop_stop()
    client.disconnect()