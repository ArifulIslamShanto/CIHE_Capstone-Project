# app.py
import os
import json
import base64
from io import BytesIO
import numpy as np
from PIL import Image
from flask import Flask, render_template, request, jsonify
import mysql.connector
import bcrypt
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

from keras_facenet import FaceNet
from mtcnn.mtcnn import MTCNN

# ------------------ CONFIG ------------------
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "hotdocuser"
USERS_TABLE = "users"
EMBED_TABLE = "facial_embeddings"

EMBED_SAMPLES_TARGET = 5
# ---------------------------------------------
# ========== EMAIL CONFIG ==========
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "console1913@gmail.com"
EMAIL_PASSWORD = "mfsimuhpkdrjpdnm"   # Use App Password for Gmail
# ===================================

app = Flask(__name__, template_folder="templates", static_folder="static")

# Load models once
embedder = FaceNet()
detector = MTCNN()

# In-memory buffers
buffers = {}         # buffers[username] = list of embeddings
pending_users = {}   # pending_users[username] = details before finalize


# ---------- DB Helpers ----------
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )

def get_user_by_username(username):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM {USERS_TABLE} WHERE username=%s", (username,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()

def user_has_embeddings(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM {EMBED_TABLE} WHERE user_id=%s", (user_id,))
        return cur.fetchone() is not None
    finally:
        cur.close(); conn.close()

def create_user(full_name, phone_number, username, email, password_plain):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        hashed = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            f"INSERT INTO {USERS_TABLE} (full_name, phone_number, username, email, password) VALUES (%s,%s,%s,%s,%s)",
            (full_name, phone_number, username, email, hashed)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close(); conn.close()

def save_average_embedding(user_id, avg_embedding):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        emb_json = json.dumps(avg_embedding.tolist())
        cur.execute(
            f"INSERT INTO {EMBED_TABLE} (user_id, average_embeddings) VALUES (%s, %s)",
            (user_id, emb_json)
        )
        conn.commit()
    finally:
        cur.close(); conn.close()


# ---------- Face Helpers ----------
def preprocess_face(image_np):
    image = Image.fromarray(image_np).convert("RGB").resize((160, 160))
    return np.asarray(image)

def extract_face_region(frame_np):
    detections = detector.detect_faces(frame_np)
    if not detections:
        return None
    det = max(detections, key=lambda d: d.get("confidence", 0))
    x, y, w, h = det["box"]
    x, y = max(0, x), max(0, y)
    return frame_np[y:y+h, x:x+w]

def get_embedding(face_np):
    return embedder.embeddings([face_np])[0]


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)


# ---------- LOGIN + OTP FLOW ----------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password required"}), 400

    user = get_user_by_username(username)
    if not user:
        return jsonify({"ok": False, "error": "Invalid username or password"}), 401

    # Verify password
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"ok": False, "error": "Invalid username or password"}), 401

    # Generate OTP
    otp = f"{random.randint(100000, 999999)}"

    # Save OTP in DB
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        generated = datetime.now()
        expiry = generated + timedelta(minutes=5)
        cur.execute(
            "INSERT INTO otp_codes (user_id, otp, generated_timestamp) VALUES (%s, %s, %s)",
            (user["id"], otp, generated)
        )
        conn.commit()
    finally:
        cur.close(); conn.close()

    # Send OTP via email
    try:
        send_email(user["email"], "Your Login OTP", f"Your OTP is {otp}. It will expire in 5 minutes.")
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to send OTP: {e}"}), 500

    # Forward to OTP entry page
    return jsonify({"ok": True, "message": "OTP sent", "redirect": "otp-page"})


@app.route("/api/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json(force=True)
    otp = data.get("otp", "").strip()

    if not otp:
        return jsonify({"ok": False, "error": "OTP required"}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT o.id, o.user_id, o.otp, o.generated_timestamp,
                   (o.generated_timestamp + INTERVAL 5 MINUTE) AS expiry
            FROM otp_codes o
            WHERE o.otp=%s
            ORDER BY o.generated_timestamp DESC
            LIMIT 1
        """, (otp,))
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()

    if not row:
        return jsonify({"ok": False, "error": "Invalid OTP"}), 401

    now = datetime.now()
    if now > row["expiry"]:
        return jsonify({"ok": False, "error": "OTP expired"}), 401

    return jsonify({"ok": True, "message": "OTP verified", "user_id": row["user_id"]})


# ---------- Routes ----------
@app.route("/", methods=["GET"])
def index():
    return render_template("register.html", embed_target=EMBED_SAMPLES_TARGET)

@app.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template("dashboard.html", embed_target=EMBED_SAMPLES_TARGET)

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html", embed_target=EMBED_SAMPLES_TARGET)

@app.route("/otp-page", methods=["GET"])
def otp_page():
    return render_template("otp-page.html", embed_target=EMBED_SAMPLES_TARGET)

@app.route("/api/register_pending", methods=["POST"])
def api_register_pending():
    """Hold user details in memory until embeddings finalized."""
    data = request.get_json(force=True)
    full_name = data.get("full_name", "").strip()
    phone_number = data.get("phone_number", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not full_name or not phone_number or not username or not email or not password:
        return jsonify({"ok": False, "error": "All fields required"}), 400

    if get_user_by_username(username):
        return jsonify({"ok": False, "error": "Username already exists"}), 409

    # Save to memory
    pending_users[username] = {
        "full_name": full_name,
        "phone_number": phone_number,
        "email": email,
        "password": password
    }
    return jsonify({"ok": True, "message": "User info stored in memory. Capture embeddings now."})

@app.route("/api/upload_frame", methods=["POST"])
def upload_frame():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    image_b64 = data.get("image", "")

    if not username or not image_b64:
        return jsonify({"ok": False, "error": "username and image are required"}), 400

    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(image_b64)
        frame = np.array(Image.open(BytesIO(img_bytes)).convert("RGB"))
    except Exception as e:
        return jsonify({"ok": False, "error": f"Invalid image data: {e}"}), 400

    face_region = extract_face_region(frame)
    if face_region is None or face_region.size == 0:
        return jsonify({"ok": False, "error": "No face detected"}), 200

    face_array = preprocess_face(face_region)
    embedding = get_embedding(face_array)

    buffers.setdefault(username, []).append(embedding)
    count = len(buffers[username])
    done = count >= EMBED_SAMPLES_TARGET

    return jsonify({"ok": True, "count": count, "done": done})

@app.route("/api/finalize", methods=["POST"])
def finalize():
    """Insert pending user + embeddings into DB once finalized."""
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"ok": False, "error": "username required"}), 400

    if username not in pending_users:
        return jsonify({"ok": False, "error": "No pending user data found"}), 400

    embs = buffers.get(username, [])
    if len(embs) < EMBED_SAMPLES_TARGET:
        return jsonify({"ok": False, "error": f"Not enough samples. Got {len(embs)}"}), 400

    # Create user in DB
    details = pending_users.pop(username)
    user_id = create_user(
        details["full_name"],
        details["phone_number"],
        username,
        details["email"],
        details["password"]
    )

    avg_emb = np.mean(np.stack(embs, axis=0), axis=0)
    save_average_embedding(user_id, avg_emb)

    buffers.pop(username, None)

    return jsonify({"ok": True, "message": "User & embeddings saved", "user_id": user_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
