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

model = tf.keras.models.load_model("plant_disease_model.keras", compile=False)

# Load class names
with open("class_names.pkl", "rb") as f:
    class_names = pickle.load(f)

app = Flask(__name__)
CORS(app)

# Initialize Firebase
firebase_key_data = json.loads(os.environ["FIREBASE_KEY"])
cred = credentials.Certificate(firebase_key_data)
firebase_admin.initialize_app(cred)

# Example: Connect to Firestore
db = firestore.client()

@app.route("/")
def home():
    return "Flask connected with Firebase ✅"

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

# Authentication
@app.route("/googleAuth",methods=["post"])
def authentication():
    try:
        id_token=request.json.get("token")
        decoded_token=auth.verify_id_token(id_token) 
        uid=decoded_token.get("uid")
        email=decoded_token.get("email")
        name=decoded_token.get("name")
        picture=decoded_token.get("picture")
        try:
            doc_ref=db.collection('users').document(uid)
            doc = doc_ref.get() 
            if not doc.exists:
                userData={
                    "message":"User Verified",
                    "email":email,
                    "name":name,
                    "id":uid,
                    "picture":picture,
                    "phone":"",
                    "pinnedMandis":[],
                    "state":"",
                    "district":"",
                    "interestedCom":[],
                }
                doc_ref =db.collection('users').add(userData)

            doc_ref=db.collection('users').document(uid)
            doc=doc_ref.get()
            data=doc.to_dict()
            newData={
                "message":"User Verified",
                "district":data["district"],
                "email":email,
                "interestedCom":data["interestedCom"],
                "name":data["name"],
                "phone":data["phone"],
                "pinnedMandis":data["pinnedMandis"],
                "state":data["state"],
                "id":data["uid"],
                "picture":data["picture"],
            }
            return jsonify(newData)
        except Exception as e:
            return jsonify({"error":str(e)}),401
    except Exception as e:
        return jsonify({"error":str(e)}),401
    
#update the user data
@app.route("/userUpdate/<user_id>",methods=["post"])
def updateData(user_id):
    try:
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
    except Exception as e:
        return jsonify({"error":str(e)}),500
    
# get table data (Tested Working)
@app.route("/getTableData",methods=["post"])
def get_table_data():
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

# get homepage graphs (Tested Working)
@app.route("/homePageGraphs/<user_id>",methods=["post"])
def getHomePageGraphs(user_id):
    body=request.get_json()
    state=body["state"]
    commodity_name=body["commodity_name"]
    startDate=body["startDate"]
    endDate=body["endDate"]
    endDate1=datetime.today().strftime("%d-%b-%Y")
    startDate1=(datetime.today() - timedelta(days=30)).strftime("%d-%b-%Y")
    docref=db.collection("users").document(user_id)
    data=docref.get().to_dict()
    pinnedMandis=data["pinnedMandis"]
    interested_Com=data["interestedCom"]
    # district = data["district"]
    top5Districts=getTopDistrict(state,commodity_name,startDate,endDate)
    top5PriceTrend={}
    for dist in top5Districts:
        top5PriceTrend[dist]=getPriceTrendForDist(state,dist,startDate,endDate,commodity_name)
    pinnedMandiComparison=getpinnedMandiComp(pinnedMandis,interested_Com,startDate1,endDate1)
    return jsonify({"topDistricts":top5Districts,"priceTrend":top5PriceTrend,"pinnedMandiComparison":pinnedMandiComparison})

# pin a mandi (Tested Working)
@app.route("/pin_mandi/<user_id>", methods=["POST"])
def pin_mandi(user_id):
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

# get all the pinned mandis (Tested and working)
@app.route("/getPinnednMadis/<user_id>",methods=["get"])
def getpinnedmandis(user_id):
    doc_ref=db.collection("users").document(user_id)
    return doc_ref.get().to_dict()["pinnedMandis"] 

# to get commodity info for a specific mandi (Tested Working)
@app.route("/getdataframe",methods=["post"])
def getdataframe():
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

def preprocess_image(img_path):

    image = Image.open(img_path).convert("RGB")
    # Resize to 160x160 (as required by your model)
    image = image.resize((160, 160))
    # Convert to numpy array
    img_array = np.array(image)
    # Add batch dimension
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

@app.route("/predict_disease",methods=["get"])
def predict_disease():
    # prediction = model.predict([request.json.get("data")])
    pred = model.predict(preprocess_image('leaf4 .png'))
    predicted_class = np.argmax(pred[0])
    disease_name = class_names[predicted_class]
    print(disease_name)
    return f"Prediction: {disease_name}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
