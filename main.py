import io
import pickle
from PIL import Image
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore, auth
from webscrapper import getTableData,getPriceTrend,getTopDistrict,getPriceTrendForDist,getpinnedMandiComp
from datetime import datetime, timedelta
from store import commodity_map, state_map, districts
import numpy as np
import tensorflow as tf
from flask_cors import CORS
import json
import os
import random
from google import genai
from dotenv import load_dotenv
load_dotenv()

model = tf.keras.models.load_model("plant_disease_model.keras", compile=False)

# Load class names
with open("class_names.pkl", "rb") as f:
    class_names = pickle.load(f)

app = Flask(__name__)
CORS(app)

# Initialize Firebase

# firebase_key_data = json.loads(os.environ["FIREBASE_KEY"]) # // For production
# cred = credentials.Certificate(firebase_key_data)


cred = credentials.Certificate("firebase_key.json") # // For local testing


firebase_admin.initialize_app(cred)

# Example: Connect to Firestore
db = firestore.client()

@app.route("/")
def home():
    return "Hello, This is the backend for Hamara Kisan!"

# for testing database connection
@app.route("/test_db")
def test_db():
    try:
        # Try to get a collection or document
        doc = db.collection("users").limit(1).get()
        if doc:
            return "Connected to Firestore! Found some data."
        else:
            return "Connected but no data in 'users' collection."
    except Exception as e:
        return f"Connection failed: {str(e)}"

# Authentication (implemented on frontend)
# @app.route("/googleAuth",methods=["post"])
# def authentication():
#     try:
#         id_token=request.json.get("token")
#         decoded_token=auth.verify_id_token(id_token) 
#         uid=decoded_token.get("uid")
#         email=decoded_token.get("email")
#         name=decoded_token.get("name")
#         picture=decoded_token.get("picture")
#         try:
#             doc_ref=db.collection('users').document(uid)
#             doc = doc_ref.get() 
#             if not doc.exists:
#                 userData={
#                     "message":"User Verified",
#                     "email":email,
#                     "name":name,
#                     "id":uid,
#                     "picture":picture,
#                     "phone":"",
#                     "pinnedMandis":[],
#                     "state":"",
#                     "district":"",
#                     "interestedCom":[],
#                 }
#                 dashboardData={
#                     "data":[],
#                     "userId":uid
#                 }
#                 db.collection('dashboard').add(dashboardData)
#                 doc_ref =db.collection('users').add(userData)

#             doc_ref=db.collection('users').document(uid)
#             doc=doc_ref.get()
#             data=doc.to_dict()
#             newData={
#                 "message":"User Verified",
#                 "district":data["district"],
#                 "email":email,
#                 "interestedCom":data["interestedCom"],
#                 "name":data["name"],
#                 "phone":data["phone"],
#                 "pinnedMandis":data["pinnedMandis"],
#                 "state":data["state"],
#                 "id":data["uid"],
#                 "picture":data["picture"],
#             }
#             return jsonify(newData)
#         except Exception as e:
#             return jsonify({"error":str(e)}),401
#     except Exception as e:
#         return jsonify({"error":str(e)}),401



#update the user data
@app.route("/userUpdate/<user_id>",methods=["post"])
def updateData(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        data=request.get_json()
        doc_ref = db.collection('users').document(user_id)
        doc_ref.update({
            "name":data["name"],
            "district":data["district"],
            "interestedCom":data["interestedCom"],
            "phone":data["phone"],
            "pinnedMandis":data["pinnedMandis"],
            "state":data["state"],
        })
        return jsonify({"success": True, "message": "User data updated successfully!"})
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401
    
# get table data (Tested Working)
@app.route("/getTableData",methods=["post"])
def get_table_data():
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        state = data["state"]
        district = data["district"]
        commodity_name = data["commodity_name"]
        startDate = data["startDate"]
        endDate = data["endDate"]
        table_data = getTableData(state, district, commodity_name, startDate, endDate)
        return jsonify(table_data)
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# get homepage graphs (Tested Working)
@app.route("/homePageGraphs/<user_id>",methods=["post"])
def getHomePageGraphs(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        body=request.get_json()
        state=body["state"]
        commodity_name=body["commodity_name"]
        startDate=body["startDate"]
        endDate=body["endDate"]
        # endDate1=datetime.today().strftime("%d-%b-%Y")
        # startDate1=(datetime.today() - timedelta(days=30)).strftime("%d-%b-%Y")
        docref=db.collection("users").document(user_id)
        data=docref.get().to_dict()
        pinnedMandis=data["pinnedMandis"]
        interested_Com=data["interestedCom"]
        # district = data["district"]
        top5Districts=getTopDistrict(state,commodity_name,startDate,endDate)
        top5PriceTrend={}   
        for dist in top5Districts:
            top5PriceTrend[dist]=getPriceTrendForDist(state,dist,startDate,endDate,commodity_name)
        return jsonify({"topDistricts":top5Districts,"priceTrend":top5PriceTrend})
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401
    
@app.route("/pinnedMandiComparison/<user_id>",methods=["POST"])
def pinnedMandiComparison(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        endDate=datetime.today().strftime("%d-%b-%Y")
        startDate=(datetime.today() - timedelta(days=30)).strftime("%d-%b-%Y")
        docref=db.collection("users").document(user_id)
        data=docref.get().to_dict()
        pinnedMandis=data["pinnedMandis"]
        interested_Com=data["interestedCom"]
        pinnedMandiComparison=getpinnedMandiComp(pinnedMandis,interested_Com,startDate,endDate)
        return jsonify({"pinnedMandiComparison":pinnedMandiComparison})
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
            "pinnedMandis": updatedData
        })
        return jsonify({
            "success": True,
            "message": "Updated records!",
            "pinnedMandis": updatedData
        }), 200
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

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
        district = data["district"]
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
            "district": district,
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

# get all the pinned mandis (Tested and working)
@app.route("/getPinnednMadis/<user_id>",methods=["get"])
def getpinnedmandis(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        doc_ref=db.collection("users").document(user_id)
        pinnedMandis=doc_ref.get().to_dict()["pinnedMandis"]
        return pinnedMandis
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# to get commodity info for a specific mandi (Tested Working)
@app.route("/getdataframe",methods=["post"])
def getdataframe():
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        data=request.get_json()
        state=data["state"]
        district=data["district"]
        market_id=data["marketid"]
        days=data["days"]
        comm=data["comm"]
        endDate=datetime.today().strftime("%d-%b-%Y")
        startDate=(datetime.today() - timedelta(days=days)).strftime("%d-%b-%Y")
        # doc_ref = db.collection("users").document(userid)
        # user_data = doc_ref.get().to_dict()
        # intCom = user_data["interestedCom"]
        res=getPriceTrend(state,district,market_id,startDate,endDate,comm)
        # print(res)
        return res
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token expired"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401

#to get user dashboard data
@app.route("/dashboard/<user_id>",methods=["get"])
def getUserData(user_id):
    id_token=request.json.get("token")
    if not id_token:
        return jsonify({"error": "Missing token"}), 400
    try:
        auth.verify_id_token(id_token)
        doc_ref=db.collection("dashboard").document(user_id)
        data=doc_ref.get().to_dict()
        return data
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
    prompt = f"You are a farming expert. My crop in my farm has {disease} disease. Suggest me the remedy for it along with reasons of disease and recommended pestisides. Give formal, precise response without any jargon. No need to greet or introduce yourself. Just give me the remedy in brief."
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
