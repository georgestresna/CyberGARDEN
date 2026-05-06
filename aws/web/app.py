from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import paho.mqtt.publish as publish
import os

app = FastAPI()

###
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)
###

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
client = None
db = None

@app.on_event("startup")
async def startup_db_client():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.cybergarden

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

###

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    cursor = db.sensors.find({}, {"_id": 0}).sort("timestamp", -1).limit(50)
    data = await cursor.to_list(length=50)

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(data)

    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "data": data})

@app.post("/api/command/pump")
async def control_pump(request: Request):
    try:
        # 1. Get the requested state from the HTML button (1 or 0)
        payload = await request.json()
        target_state = payload.get("state", 1) 
        
        # 2. Convert to string because MQTT payloads must be strings/bytes
        mqtt_payload = str(target_state)

        # 3. Publish to Mosquitto
        publish.single(
            topic="cybergarden/commands/pump",
            payload=mqtt_payload,
            hostname="mosquitto", 
            port=1883
        )

        await db.commands.insert_one({
            "device": "pump",
            "state": target_state,
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        })
        
        return {"status": "success", "state": target_state}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/api/command/pulse")
async def trigger_water_pulse():
    """
    Triggers a 5-second watering pulse. 
    Sends '1' to MQTT and logs the event to MongoDB.
    """
    try:
        # 1. Publish to Mosquitto (The Pi will hear this and forward to STM32)
        # We hardcode "1" here because this specific route is ONLY for turning it on.
        publish.single(
            topic="cybergarden/commands/pump",
            payload="1",
            hostname="mosquitto", 
            port=1883
        )

        # 2. Log this manual action into MongoDB for history/auditing
        await db.commands.insert_one({
            "device": "pump",
            "action": "manual_pulse_5s",
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        })

        return {"status": "success", "message": "Pulse command sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}