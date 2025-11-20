import io
import pickle
from PIL import Image
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime, timedelta
import numpy as np
import tensorflow as tf
from flask_cors import CORS
import json
import os
import random
import requests
from store import comm_id, state_market_map,state_id_map
from google import genai
# from dotenv import load_dotenvs


# load_dotenv()

model = tf.keras.models.load_model("plant_disease_model.keras", compile=False)

# Load class names
with open("class_names.pkl", "rb") as f:
    class_names = pickle.load(f)

app = Flask(__name__)

#Cross origin resource sharing
CORS(app)


cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

#firestore handle
db=firestore.client()

@app.route("/")
def home():
    return "Hello, This is the backend for Hamara Kisan!"

#get table data
@app.route("/getTableData",methods=["POST"])
def getTableData():
    auth.verify_id_token(id_token)
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
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
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# pin a mandi
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

#unpin a mandi
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
        updated_pinnedMandis = [mandi for mandi in pinnedMandis if mandi.get("id") != mandi_id]
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
    
def preprocess_image(uploaded_file):

    # Read image bytes from the uploaded file
    image = Image.open(io.BytesIO(uploaded_file.read())).convert("RGB")
    
    # Resize to model input size
    image = image.resize((160, 160))
    
    img_array = np.array(image, dtype=np.float32)
    
    # # Normalize if needed 
    # img_array = img_array / 255.0
    
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array

def getRemedyFromAi(disease):
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    prompt = f"You are a farming expert. My crop in my farm has {disease} disease. Suggest me the remedy for it along with recommended pestisides. Give formal, precise response without any jargon. No need to greet or introduce yourself. Just give me the remedy in brief."
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    print(response.text)
    return response.text

@app.route("/predict_disease",methods=["post"])
def predict_disease():
    id_token=request.form.get('token')
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
    
        file = request.files['file']
        print("File is : ", file)

        # prediction = model.predict([request.json.get("data")])
        pred = model.predict(preprocess_image(file))
        predicted_class = np.argmax(pred[0])
        disease_name = class_names[predicted_class]
        print(disease_name)
        isNotDiseased = ("healthy" in disease_name) or (disease_name == "Background_without_leaves")
        return jsonify({"disease": disease_name, "isDiseased": not isNotDiseased})
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/getRemedy",methods=["post"])
def getRemedy():
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        body=request.get_json()
        disease=body["disease"]
        return jsonify({"data": getRemedyFromAi(disease)})
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/addRecord/<user_id>",methods=["POST"])
def addRecord(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        body=request.get_json()
        newEntry={}
        newEntry["commodity"]=body["commodity"]
        newEntry["date"]=body["date"]
        newEntry["price"]=body["price"]
        newEntry["quantity"]=body["quantity"]
        newEntry["total"]=body["price"]*body["quantity"]

        doc_ref=db.collection("dashboard").document(user_id)

        prevData=doc_ref.get().to_dict().get("data")
        rand=random.randint(10000, 99999)
        newEntry["index"]=user_id+str(rand)
        prevData.append(newEntry)
        print(prevData)
        doc_ref.update({
            "data": prevData
        })
        return jsonify({
            "success": True,
            "message": "Entry Created successfully!",
            "data": prevData
        }), 200
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

#Delete Record
@app.route("/deleteRecord/<user_id>",methods=["POST"])
def deleteRecord(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        body=request.get_json()
        index=body["index"]
        doc_ref=db.collection("dashboard").document(user_id)
        data=doc_ref.get().to_dict().get("data")
        print(data)
        updatedData = [m for m in data if m.get("index") != index]
        doc_ref.update({
            "data": updatedData
        })
        return jsonify({
            "success": True,
            "message": "Updated records!",
            "data": updatedData
        }), 200
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401
    
# Main graph trend for all the pinnedMandis for all the interested commodities
@app.route("/maingraph/<user_id>", methods=["POST"])
def mainGraph(user_id):
    doc_ref = db.collection("users").document(user_id)
    data = doc_ref.get().to_dict()
    interested_comms = data.get("interestedCom")
    pinned_mandis = data.get("pinnedMandis")
    res = {}
    for comm in interested_comms:
        commid = comm_id[comm]["cid"]
        foracomm = {}
        for mandi in pinned_mandis:
            market_id = mandi["id"]
            state = mandi["state"]
            state_id = state_id_map[state]
            marketName = mandi["marketName"]
            url = (
                "https://api.agmarknet.gov.in/v1/prices-and-arrivals/commodity-price/lastweek?"
                f"marketId={market_id}&stateId={state_id}&commodityId={commid}&includeExcel=false"
            )
            data = requests.get(url).json()
            item = data["data"][0]
            # remove first and last key
            keys = list(item.keys())[1:-1]
            priceTrend = []
            for k in keys:
                price = item[k]
                # skip NA/NR/empty prices
                if not isinstance(price, (int, float)):
                    continue
                priceTrend.append({
                    "date": k,
                    "price": price
                })
            if priceTrend:
                foracomm[marketName] = priceTrend

        if foracomm:
            res[comm] = foracomm

    return jsonify(res)
