from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore, auth
from webscrapper import getTableData
app = Flask(__name__)

# Initialize Firebase
cred = credentials.Certificate("firebase_key.json")  # path to your key file
firebase_admin.initialize_app(cred)

# Example: Connect to Firestore
db = firestore.client()

@app.route("/")
def home():
    return "Flask connected with Firebase ✅"

# # Example: Add data to Firestore
# @app.route("/add_user", methods=["POST"])
# def add_user():
#     data = request.json
#     doc_ref = db.collection("users").add(data)
#     return jsonify({"success": True, "id": doc_ref[1].id})


# Authentication
@app.route("/googleAuth",methods=["post"])
def authentication():
    try:
        id_token=request.json.get("token")
        decoded_token=auth.verify_id_token(id_token)
        uid=decoded_token["uid"]
        email=decoded_token.get("email")
        name=decoded_token.get("name")
        picture=decoded_token.get("picture")
        return jsonify({
            "message":"User Verified",
            "uid":uid,
            "email":email,
            "name":name,
            "picture":picture
        })
    except Exception as e:
        return jsonify({"error":str(e)}),401
    

# Example: Read data
@app.route("/users")
def get_users():
    users = db.collection("users").stream()
    result = [{**doc.to_dict(), "id": doc.id} for doc in users]
    return jsonify(result)

# Example: Read data
@app.route("/getTableData")
def getData():
    data = getTableData()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
