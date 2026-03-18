from fastapi import FastAPI
import json
import os

app = FastAPI()

###
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_FILE = os.path.join(PROJECT_ROOT, "data.json")
###
with open(DATA_FILE, "r") as file:
    data = json.load(file)

# @app.get("/api/sensors")
# def get_sensors():
#     # Read from your JSON file
#     file_path = os.path.join(os.path.dirname(__file__), 'data.json')
#     try:
#         with open(file_path, 'r') as file:
#             return json.load(file)
#     except FileNotFoundError:
#         return {"error": "data.json not found"}

@app.get("/")
async def root():
    return data