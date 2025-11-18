import io
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
from store import comm_id, state_market_map
from google import genai
from dotenv import load_dotenv
load_dotenv()

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
    group_id=comm_id[comm]["gid"]
    commid=comm_id[comm]["cid"]

    url="https://api.agmarknet.gov.in/v1/prices-and-arrivals/market-report/specific?date=2025-11-12&commodityGroupId="+str(group_id)+"&commodityId="+str(commid)+"&includeExcel=false"

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
            "market_id": str(state_market_map[body["state"]][m["marketName"]]),
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

# pin a mandi (Tested Working)
@app.route("/pin_mandi/<user_id>", methods=["POST"])
def pin_mandi(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        data = request.get_json() 
        doc_ref = db.collection("users").document(user_id)
        mandi_id = data["market_id"]
        marketName = data["marketName"]
        state = data["state"]
        # district = data["district"]
        user_doc = doc_ref.get()
        if not user_doc.exists:
            return jsonify({"success": False, "message": "User not found"}), 404
        prevPinnedMandis = user_doc.to_dict().get("pinnedMandis") or []

        if any(mandi.get("id") == mandi_id for mandi in prevPinnedMandis):
            return jsonify({
                "success": False,
                "message": f"Mandi '{marketName}' is already pinned.",
                "pinnedMandis": prevPinnedMandis
            }), 400
        prevPinnedMandis.append({
            "state": state,
            # "district": district,
            "id": mandi_id,
            "marketName": marketName
        })
        doc_ref.update({
            "pinnedMandis": prevPinnedMandis
        })
        return jsonify({
            "success": True,
            "message": "Mandi pinned successfully!",
            "pinnedMandis": prevPinnedMandis
        }), 200
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/unpinMandi/<user_id>",methods=["POST"])
def unpin_mandi(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        body=request.get_json()
        mandi_id=body["id"]
        doc_ref=db.collection("users").document(user_id)
        pinnedMandis=doc_ref.get().to_dict().get("pinnedMandis")
        updated_pinnedMandis = [m for m in pinnedMandis if m.get("id") != mandi_id]
        doc_ref.update({
            "pinnedMandis": updated_pinnedMandis
        })
        return jsonify({
            "success": True,
            "message": "Mandi UnPinned successfully!",
            "pinnedMandis": updated_pinnedMandis
        }), 200
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401