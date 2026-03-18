from fastapi import FastAPI
import json
# import os

app = FastAPI()

###
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
# PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
# DATA_FILE = os.path.join(PROJECT_ROOT, "data.json")
DATA_FILE = "/db/data.json"
###

@app.get("/")
async def root():

    with open(DATA_FILE, "r") as file:
        data = json.load(file)


    return data