from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import os

app = FastAPI()

###
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# FRONT_ROOT = os.path.dirname(CURRENT_DIR)
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "templates")
# PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
# DATA_FILE = os.path.join(PROJECT_ROOT, "data.json")
DATA_FILE = "/db/data.json"
###
templates = Jinja2Templates(directory=TEMPLATE_DIR)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    with open(DATA_FILE, "r") as file:
        data = json.load(file)
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(data)

    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "data": data})