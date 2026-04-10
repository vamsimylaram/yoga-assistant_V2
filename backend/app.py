import os
import time
import base64
import cv2
import numpy as np
import mediapipe as mp
import cloudinary
import cloudinary.uploader
import google.generativeai as genai
from bson import ObjectId
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv 
import pymongo 
import bcrypt  

# ⬅️ IMPORT: Orchestrator from your controllers folder
from controllers.app_controller import YogaAppController 

# --- Configuration ---
load_dotenv()

CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"] 
UPLOAD_FOLDER = 'temp_uploads'

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- NEW: Cloudinary & Gemini Configuration ---
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- MongoDB Connection Setup ---
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    db = mongo_client['yoga_app_db'] 
    users_collection = db['users'] 
    chats_collection = db['chats'] # NEW: Collection for storing chat history  
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")

# --- Global Controller Loading ---
APP_CONTROLLER = None
try:
    APP_CONTROLLER = YogaAppController()
    print("✅ AI Controller initialized successfully (VLM + RAG ready)")
except Exception as e:
    print(f"❌ AI Controller initialization failed: {e}")


# --- MediaPipe Setup ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

# --- Utility Functions ---
def base64_to_temp_file(data_url: str):
    if not data_url:
        return None
    try:
        if ',' in data_url:
            _, encoded = data_url.split(',', 1)
        else:
            encoded = data_url
            
        data = base64.b64decode(encoded)
        filename = secure_filename(f"upload_{int(time.time())}.jpg")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(file_path, 'wb') as f:
            f.write(data)
            
        return file_path
    except Exception as e:
        print(f"Error converting base64 to file: {e}")
        return None

def calculate_angle(a, b, c):
    a = np.array(a) 
    b = np.array(b) 
    c = np.array(c) 
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

def get_pose_data(image_path):
    try:
        image = cv2.imread(image_path)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if not results.pose_landmarks:
            return None

        landmarks = results.pose_landmarks.landmark

        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
        
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

        return {
            "Left Elbow Angle": round(calculate_angle(left_shoulder, left_elbow, left_wrist), 2),
            "Right Elbow Angle": round(calculate_angle(right_shoulder, right_elbow, right_wrist), 2),
            "Left Knee Angle": round(calculate_angle(left_hip, left_knee, left_ankle), 2),
            "Right Knee Angle": round(calculate_angle(right_hip, right_knee, right_ankle), 2)
        }
    except Exception as e:
        print(f"Error processing MediaPipe math: {e}")
        return None

# --- NEW: Title Generator Function ---
def generate_chat_title(query):
    """Uses Gemini to generate a short, 2-3 word title for the sidebar."""
    fallback_title = " ".join(query.split()[:3]) + "..." 
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Summarize this user query into a 2 to 4 word yoga pose name or topic. Only return the title, no extra text: '{query}'"
        response = model.generate_content(prompt)
        if response.text:
            return response.text.strip().replace('"', '')
    except Exception as e:
        print(f"Title generation failed: {e}")
    return fallback_title


# --- AUTH ROUTES ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and Password are required"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password
    })
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = users_collection.find_one({"email": email})

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({
            "message": "Login successful", 
            "name": user.get('name', 'User'),
            "email": user.get('email')
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# --- RAG/Chat Routes ---
@app.route('/api/chat', methods=['POST'])
def chat():
    if not APP_CONTROLLER:
        return jsonify({"answer": "Server is still loading the AI models. Please wait a moment."}), 503

    data = request.json
    user_query = data.get('query', '')
    image_data_url = data.get('image_data', None)
    
    # NEW: Grab email and chat_id from the React payload
    email = data.get('email')
    chat_id = data.get('chat_id') 

    if not email:
        return jsonify({"error": "User email is required to save chat history."}), 400

    image_path = None
    cloudinary_image_url = None # NEW: Store Cloudinary URL
    
    print(f"Received query from UI: {user_query[:50]}...")
    
    try:
        # 1. Handle Image Upload & Run Math
        if image_data_url:
            print("Image data detected. Saving temporarily...")
            image_path = base64_to_temp_file(image_data_url)
            
            if not image_path:
                return jsonify({"answer": "Failed to process image data."}), 400

            # --- Inject Telemetry Data into the prompt ---
            pose_angles = get_pose_data(image_path)
            if pose_angles:
                telemetry_text = "\n\n[SYSTEM TELEMETRY DATA - JOINT ANGLES CALCULATED VIA MEDIAPIPE]:\n"
                for joint, angle in pose_angles.items():
                    telemetry_text += f"- {joint}: {angle}°\n"
                
                telemetry_text += "\nINSTRUCTIONS: Cross-reference the visual image with the specific mathematical telemetry angles provided above to give highly accurate structural feedback."
                
                user_query = user_query + telemetry_text
                print("✅ Successfully injected MediaPipe telemetry into the AI prompt.")
            else:
                print("⚠️ MediaPipe could not detect clear body landmarks. Proceeding with visual AI only.")

            # --- NEW: Upload to Cloudinary ---
            print("Uploading image to Cloudinary...")
            upload_result = cloudinary.uploader.upload(
                image_path, 
                folder="yoga_poses"
            )
            cloudinary_image_url = upload_result.get("secure_url") 
            print(f"✅ Uploaded to Cloudinary: {cloudinary_image_url}")

        # 2. Call the Orchestrator
        final_answer = APP_CONTROLLER.process_user_request(image_path, user_query)
        
        # 3. --- NEW: Database Saving Logic ---
        message_record = {
            "sender": "user",
            "text": data.get('query', ''), # Save original query, not the injected math
            "image_url": cloudinary_image_url, 
            "bot_response": final_answer,
            "timestamp": time.time()
        }

        if not chat_id:
            # Create a brand new chat session
            new_title = generate_chat_title(data.get('query', ''))
            new_chat = {
                "email": email,
                "title": new_title,
                "created_at": time.time(),
                "messages": [message_record]
            }
            result = chats_collection.insert_one(new_chat)
            chat_id = str(result.inserted_id)
        else:
            # Append to an existing chat session
            chats_collection.update_one(
                {"_id": ObjectId(chat_id)},
                {"$push": {"messages": message_record}}
            )

        # Return the final answer AND the chat_id
        return jsonify({
            "answer": final_answer,
            "chat_id": chat_id
        })

    except Exception as e:
        print(f"An error occurred during AI processing: {e}")
        return jsonify({"answer": "An unexpected error occurred while processing your request."}), 500

    finally:
        # 4. Clean up the temporary image file (it is safe in Cloudinary now)
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"Cleaned up temporary file: {image_path}")
            except Exception as e:
                print(f"Error during file cleanup: {e}")


# --- NEW: Fetch All Chats for Sidebar ---
@app.route('/api/chats/<email>', methods=['GET'])
def get_user_chats(email):
    chats = list(chats_collection.find({"email": email}).sort("created_at", -1))
    
    sidebar_data = []
    for chat in chats:
        sidebar_data.append({
            "id": str(chat['_id']),
            "title": chat.get('title', 'New Chat'),
            "created_at": chat.get('created_at')
        })
        
    return jsonify(sidebar_data), 200


# --- NEW: Fetch Specific Chat History ---
@app.route('/api/chat/<chat_id>', methods=['GET'])
def get_single_chat(chat_id):
    try:
        chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
            
        formatted_messages = []
        for msg in chat['messages']:
            user_msg = {"sender": "user", "text": msg['text']}
            # Use image_url if it exists, otherwise it will just display text
            if msg.get('image_url'):
                user_msg['image_url'] = msg['image_url'] 
            formatted_messages.append(user_msg)
            
            bot_msg = {"sender": "bot", "text": msg['bot_response']}
            formatted_messages.append(bot_msg)
            
        return jsonify({
            "chat_id": str(chat['_id']),
            "title": chat['title'],
            "messages": formatted_messages
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid Chat ID"}), 400


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple endpoint to check if the server is running."""
    status = "OK" if APP_CONTROLLER else "FAILED"
    return jsonify({
        "status": status, 
        "ai_controller_ready": APP_CONTROLLER is not None
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
