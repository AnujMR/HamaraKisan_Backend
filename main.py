import pickle
from PIL import Image
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore, auth
from webscrapper import getTableData,getPriceTrend,getTopDistrict
from datetime import datetime, timedelta

app = Flask(__name__)

# Initialize Firebase
cred = credentials.Certificate("firebase_key.json")  # path to your key file
firebase_admin.initialize_app(cred)

# Example: Connect to Firestore
db = firestore.client()

current_markets = {}

@app.route("/")
def home():
    return "Flask connected with Firebase ✅"

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
    
# get table data
@app.route("/getTableData",methods=["post"])
def gettableData():
    data=request.get_json()
    state=data["state"]
    district = data["district"]
    commodity_name=data["commodity_name"]
    startDate=data["startDate"]
    endDate=data["endDate"]
    table_data = getTableData(state,district,commodity_name,startDate,endDate)
    current_markets = table_data["market_ids"]
    top5Districts=getTopDistrict(state,commodity_name,startDate,endDate)
    return jsonify({"tableData":table_data["data"],"topDistricts":top5Districts})

# pin a mandi
@app.route("/pin_mandi/<user_id>",methods=["post"])
def pin_mandi(user_id):
    data=request.get_json()
    doc_ref=db.collection("users").document(user_id)
    mandi_id=current_markets[data["market_name"]]
    prevPinnedMadis=doc_ref.get().to_dict()["pinnedMandis"]
    currentPinnedMandis=prevPinnedMadis.append({"state":data["state"],"district":data["district"],"id":mandi_id})
    print(currentPinnedMandis)
    doc_ref.update({
        "pinnedMandis":currentPinnedMandis
    })

# get all the pinned mandis
@app.route("/getPinnednMadis/<user_id>",methods=["get"])
def getpinnedmandis(user_id):
    doc_ref=db.collection("users").document(user_id)
    return doc_ref.get().to_dict()["pinnedMandis"] 

# to get commodity info for a specific mandi
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

# @app.route("/topdistrict",methods=["post"])
# def gettopdistrict():
#     data=request.get_json()
#     state=data["state"]
#     days=data["days"]
#     comm=data["comm"]
#     endDate=datetime.today().strftime("%d-%b-%Y")
#     startDate=(datetime.today() - timedelta(days=days)).strftime("%d-%b-%Y")
#     s=getTopDistrict(state,comm,startDate,endDate)
#     return res

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
    app.run(debug=True)
