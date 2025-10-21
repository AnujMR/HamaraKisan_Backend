from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore, auth
from webscrapper import getTableData,getData
from datetime import datetime,timedelta
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
    return jsonify(table_data["data"])

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
@app.route("/getdataframe/<userid>",methods=["post"])
def getdataframe(userid):
    print(userid)
    data=request.get_json()
    state=data["state"]
    district=data["district"]
    market_id=data["marketid"]
    days=data["days"]
    startDate=datetime.today().strftime("%d-%b-%Y")
    endDate=(datetime.today() - timedelta(days=days)).strftime("%d-%b-%Y")
    print(data)
    doc_ref=db.collection("users").document(userid)
    intCom=doc_ref.get().to_dict()["interestedCom"]
    print(intCom)
    res=getData(state,district,market_id,intCom,startDate,endDate)
    print(res)
    return res

if __name__ == "__main__":
    app.run(debug=True)
