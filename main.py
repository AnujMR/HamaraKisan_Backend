import pickle
from PIL import Image
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore, auth
# from webscrapper import getTableData,getPriceTrend,getTopDistrict,getPriceTrendForDist,getpinnedMandiComp
from datetime import datetime, timedelta
# from store import commodity_map, state_map, districts
import numpy as np
import tensorflow as tf
from flask_cors import CORS
import json
import os
import random
import requests

model = tf.keras.models.load_model("plant_disease_model.keras", compile=False)

# Load class names
with open("class_names.pkl", "rb") as f:
    class_names = pickle.load(f)

app = Flask(__name__)
CORS(app)


cred = credentials.Certificate("firebase_key.json")

firebase_admin.initialize_app(cred)


db=firestore.client()

@app.route("/")
def home():
    return "Hello, This is the backend for Hamara Kisan!"


@app.route("/getTableData",methods=["POST"])
def getTableData():
    body=request.get_json()
    stateName=body["state"]
    comm=body["comm"]
    date=body["date"]

    url="https://api.agmarknet.gov.in/v1/prices-and-arrivals/market-report/specific?date=2025-11-12&commodityGroupId=1&commodityId=1&includeExcel=false"

    response=requests.get(url).json()

    markets=[]
    for state in response.get("states", []):
            if state.get("stateName") == stateName:
                markets=state.get("markets",[])
    mandis=[]
    for m in markets:
        if not m.get("data"):
            continue
        d = m["data"][0] 
        mandis.append({
            "market_name": m["marketName"],
            "min_price": d["minimumPrice"],
            "max_price": d["maximumPrice"],
            "modal_price": d["modalPrice"],
            "variety": d["variety"],
            "grade": d["grade"],
            "state":stateName,
            "comm":comm,
            "date":date
        })
    return {"mandis":mandis}