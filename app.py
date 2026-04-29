from flask import Flask, request, jsonify, render_template, session
import requests
import os
from collections import deque
import logging
import uuid

from emotion_camera import get_emotion, start_camera, stop_camera

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")

HF_TOKEN = os.getenv("HF_TOKEN")

user_emotion_histories = {}

logging.basicConfig(level=logging.INFO)


# ---------- AI FUNCTION ----------
def ask_ai(question):
    if not HF_TOKEN:
        return None

    API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    try:
        res = requests.post(API_URL, headers=headers, json={"inputs": question}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                return data[0].get("generated_text", "")
    except:
        return None

    return None


# ---------- SMART REPLY ----------
def generate_reply(msg, emotion):
    if emotion == "sad":
        return "I'm here with you. Want to share what's bothering you?"
    elif emotion == "anxious":
        return "It sounds like things feel overwhelming. Try taking a slow breath. I'm listening."
    elif emotion == "happy":
        return "That's nice to hear 😊 What's making you feel good?"
    else:
        return "I'm here to listen. Tell me anything."


# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/emotion")
def emotion():
    face = get_emotion()
    if face in ["no_face", "camera_error"]:
        face = "neutral"
    return jsonify({"face": face})


@app.route("/camera/start", methods=["POST"])
def cam_start():
    start_camera()
    return jsonify({"status": "started"})


@app.route("/camera/stop", methods=["POST"])
def cam_stop():
    stop_camera()
    return jsonify({"status": "stopped"})


# ---------- CHAT ----------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json

    if not data or not isinstance(data.get("message"), str):
        return jsonify({"error": "Invalid input"}), 400

    msg = data["message"][:500].lower()
    typing_time = data.get("typing_time", 0)
    key_count = data.get("key_count", 0)
    backspace_count = data.get("backspace_count", 0)

    # ---------- FACE ----------
    face = get_emotion()
    if face in ["no_face", "camera_error"]:
        face = "neutral"

    # ---------- GREETING OVERRIDE ----------
    if any(greet in msg for greet in ["hello", "hi", "hey", "how are you"]):
        return jsonify({
            "reply": "Hey there! 😊 How can I help you today?",
            "emotion": "neutral",
            "face": face
        })

    # ---------- CRISIS ----------
    crisis_keywords = [
        "suicide", "kill myself", "end my life",
        "want to die", "hurt myself", "not worth living"
    ]
    if any(word in msg for word in crisis_keywords):
        return jsonify({
            "reply": "I'm really sorry you're feeling this way. You are not alone.\n\n📞 Kiran Helpline: 1800-599-0019\n📞 AASRA: +91-9820466726",
            "emotion": "critical",
            "face": face
        })

    # ---------- TEXT ----------
    if any(w in msg for w in ["sad", "down", "depressed", "alone"]):
        text = "sad"
    elif any(w in msg for w in ["happy", "good", "great"]):
        text = "happy"
    elif any(w in msg for w in ["stress", "worried", "anxious"]):
        text = "anxious"
    else:
        text = "neutral"

    # ---------- TYPING ----------
    if backspace_count > 5:
        typing = "anxious"
    elif typing_time > 10:
        typing = "sad"
    elif typing_time < 2 and key_count > 20:
        typing = "anxious"
    else:
        typing = "neutral"

    # ---------- SCORING ----------
    score = {"happy": 0, "sad": 0, "anxious": 0, "neutral": 0}

    score[face] += 2     # 🔥 reduced (was 4)
    score[text] += 3     # 🔥 increased
    score[typing] += 2

    # ---------- FINAL EMOTION ----------
    if text != "neutral":
        final = text
    else:
        final = max(score, key=score.get)

    # ---------- SESSION ----------
    sid = session.get("uid")
    if not sid:
        sid = str(uuid.uuid4())
        session["uid"] = sid

    if sid not in user_emotion_histories:
        user_emotion_histories[sid] = deque(maxlen=10)

    user_emotion_histories[sid].append(final)
    history = user_emotion_histories[sid]

    # ---------- PATTERN ----------
    if list(history).count("sad") >= 5:
        insight = "\n\nI've noticed you seem sad lately. You're not alone."
    else:
        insight = ""

    reply = generate_reply(msg, final) + insight

    # ---------- AI ----------
    ai = ask_ai(f"[User feels {final}] {msg}")
    if ai and len(ai) > 5:
        reply = ai + insight

    return jsonify({
        "reply": reply,
        "emotion": final,
        "face": face
    })


# ---------- RUN ----------
if __name__ == "__main__":
    print("🚀 Running Emotion Chatbot")
    app.run(debug=True, port=5001)