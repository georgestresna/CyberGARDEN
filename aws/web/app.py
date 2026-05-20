from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import paho.mqtt.publish as publish
import os

app = FastAPI()

###
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")
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
    

##MANUAL COMMANDS
@app.post("/api/command/water")
async def trigger_water():
    """
    Triggers a 5-second watering pulse. 
    Sends '1' to MQTT and logs the event to MongoDB.
    """
    try:
        publish.single(
            topic="cybergarden/commands/pump",
            payload="1",
            hostname="mosquitto", 
            port=1883
        )

        await db.commands.insert_one({
            "device": "pump",
            "action": "manual_pulse_5s",
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        })

        return {"status": "success", "message": "Watering command sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/api/command/fan")
async def trigger_fan():
    """Send a 5-second pulse command to the fan."""
    try:
        publish.single(
            topic="cybergarden/commands/fan",
            payload="1",
            hostname="mosquitto", 
            port=1883
        )
        
        await db.commands.insert_one({
            "device": "fan",
            "action": "manual_pulse_5s",
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        })
        
        return {"status": "success", "message": "Fan command sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

##
@app.get("/api/latest")
async def get_latest_data():
    """Returns the single most recent sensor reading."""
    doc = await db.sensors.find_one({}, sort=[("timestamp", -1)])
    if doc:
        doc["_id"] = str(doc["_id"]) # MongoDB ObjectIds break JSON, must be string
        return doc
    return {}

@app.get("/api/history")
async def get_history(range: str = "6h"):
    """Returns an array of sensor data for the Chart.js graph."""
    now = datetime.now()
    
    # --- ADD THE 30m OPTION HERE ---
    if range == "30m":
        delta = timedelta(minutes=30)
    elif range == "6h":
        delta = timedelta(hours=6)
    elif range == "24h":
        delta = timedelta(hours=24)
    elif range == "7j":
        delta = timedelta(days=7)
    else:
        delta = timedelta(hours=6) # Default
        
    start_time = now - delta
    
    # Fetch all records since the start time, sorted chronologically
    cursor = db.sensors.find({"timestamp": {"$gte": start_time.isoformat()}}).sort("timestamp", 1)
    docs = await cursor.to_list(length=2000) # Limit to prevent browser crash on huge data
    
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        
    return docs

@app.get("/api/alerts")
async def get_alerts(limit: int = 10):
    """Returns the latest command logs to display as recent alerts/actions."""
    cursor = db.commands.find().sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        
    return docs

@app.get("/api/report/today")
async def get_today_report():
    """Calculates the daily averages for the report table."""
    # Start of today (midnight)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Fetch today's sensors
    cursor = db.sensors.find({"timestamp": {"$gte": today_start.isoformat()}})
    sensors = await cursor.to_list(length=None)
    
    # 2. Fetch today's watering commands
    cmd_cursor = db.commands.find({
        "timestamp": {"$gte": today_start.isoformat()}, 
        "action": "manual_pulse_5s"
    })
    commands = await cmd_cursor.to_list(length=None)
    
    # 3. Calculate averages
    if not sensors:
         return {
             "date": datetime.now().isoformat(),
             "temp_moyenne": None, "humidite_air_moyenne": None, 
             "luminosite_moyenne": None, "nb_arrosages": len(commands), 
             "volume_eau_l": round(len(commands) * 0.1, 2) # Assuming 100ml per 5s pulse
         }

    avg_temp = round(sum(s.get("temperature", 0) for s in sensors) / len(sensors), 1)
    avg_hum = round(sum(s.get("humidite", 0) for s in sensors) / len(sensors), 1)
    avg_lum = round(sum(s.get("lumiere", 0) for s in sensors) / len(sensors), 1)
    avg_soil = round(sum(s.get("soil_moisture", 0) for s in sensors) / len(sensors), 1)
    
    return {
        "date": datetime.now().isoformat(),
        "temp_moyenne": avg_temp,
        "humidite_air_moyenne": avg_hum,
        "humidite_sol_moyenne": avg_soil,
        "luminosite_moyenne": avg_lum,
        "nb_arrosages": len(commands),
        "volume_eau_l": round(len(commands) * 0.1, 2)
    }

@app.get("/api/report/1h")
async def get_report_1h():
    """Generates a summary report for the last hour."""
    one_hour_ago = datetime.now() - timedelta(hours=1)
    query = {"timestamp": {"$gte": one_hour_ago.isoformat()}}
    
    # Fetch data
    cursor = db.sensors.find(query)
    sensors = await cursor.to_list(length=1000)
    
    # Fetch commands sent in the last hour
    cmd_cursor = db.commands.find(query)
    commands = await cmd_cursor.to_list(length=100)
    
    if not sensors:
        return {"date": "Heure écoulée", "message": "Aucune donnée"}

    # Calculate averages
    avg_temp = round(sum(s.get("temperature", 0) for s in sensors) / len(sensors), 1)
    avg_hum = round(sum(s.get("humidite", 0) for s in sensors) / len(sensors), 1)
    avg_soil = round(sum(s.get("humidite_sol", 0) for s in sensors) / len(sensors), 1)
    avg_lum = round(sum(s.get("lumiere", 0) for s in sensors) / len(sensors), 1)
    
    return {
        "date": "Dernière Heure",
        "temp_moyenne": avg_temp,
        "humidite_air_moyenne": avg_hum,
        "humidite_sol_moyenne": avg_soil,
        "luminosite_moyenne": avg_lum,
        "nb_arrosages": len(commands),
        "volume_eau_l": round(len(commands) * 0.1, 2)
    }

## TEST, LATEST DATA IN DB
@app.get("/api/test")
async def test_db_connection():
    """Debug route to test if MongoDB is actually holding data"""
    try:
        # Count how many documents are in the sensors collection
        doc_count = await db.sensors.count_documents({})
        
        # Grab just one document to inspect its structure
        sample_doc = await db.sensors.find_one({}, sort=[("timestamp", -1)])
        
        if sample_doc:
            sample_doc["_id"] = str(sample_doc["_id"]) # Fix the ObjectID for JSON
            
        return {
            "status": "success",
            "message": "Connected to MongoDB successfully!",
            "total_sensor_records": doc_count,
            "sample_data": sample_doc
        }
    except Exception as e:
        return {
            "status": "CRITICAL_ERROR",
            "message": str(e)
        }