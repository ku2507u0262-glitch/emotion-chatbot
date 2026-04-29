import cv2
from deepface import DeepFace
from collections import Counter
import threading
import time

# ---------- GLOBAL STATE ----------
current_emotion = "neutral"
camera_running = False
camera_thread = None


# ---------- EMOTION DETECTION ----------
def detect_emotion(frame):
    try:
        result = DeepFace.analyze(
            frame,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='opencv'
        )

        emotion_data = result[0]['emotion']

        # ✅ Map DeepFace outputs to your simplified system
        if emotion_data.get("happy", 0) > 25:
            return "happy"

        elif emotion_data.get("sad", 0) > 25:
            return "sad"

        # Map multiple negative emotions → anxious
        elif (
            emotion_data.get("angry", 0) > 20 or
            emotion_data.get("fear", 0) > 20 or
            emotion_data.get("disgust", 0) > 20
        ):
            return "anxious"

        else:
            return "neutral"

    except Exception:
        return "neutral"


# ---------- CAMERA LOOP ----------
def camera_loop():
    global current_emotion, camera_running

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        current_emotion = "camera_error"
        camera_running = False
        return

    while camera_running:
        emotions = []

        # Take multiple frames for stability
        for _ in range(3):
            ret, frame = cap.read()
            if not ret:
                continue

            emotions.append(detect_emotion(frame))

        if emotions:
            # Pick most common emotion
            current_emotion = Counter(emotions).most_common(1)[0][0]
        else:
            current_emotion = "no_face"

        time.sleep(1.2)

    cap.release()


# ---------- START CAMERA ----------
def start_camera():
    global camera_running, camera_thread

    if camera_running:
        return  # already running

    camera_running = True
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()


# ---------- STOP CAMERA ----------
def stop_camera():
    global camera_running
    camera_running = False


# ---------- GET CURRENT EMOTION ----------
def get_emotion():
    return current_emotion