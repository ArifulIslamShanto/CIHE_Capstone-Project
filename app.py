from flask import Flask, render_template, Response
import cv2

app = Flask(__name__)

# Load Haar cascades
frontal_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
profile_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')

camera = None  # Will open only on demand

def generate_frames():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)

    while True:
        success, frame = camera.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = frontal_face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80,80))
        profiles = profile_face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80,80))

        all_faces = list(faces) + list(profiles)

        # Only draw on the closest face (largest area)
        if all_faces:
            x, y, w, h = max(all_faces, key=lambda rect: rect[2]*rect[3])
            center = (x + w // 2, y + h // 2)
            axes = (w // 2, int(h * 0.6))  # tall oval
            cv2.ellipse(frame, center, axes, 0, 0, 360, (0,255,0), 3)

        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_camera')
def stop_camera():
    global camera
    if camera:
        camera.release()
        camera = None
    return "Camera stopped"

if __name__ == "__main__":
    app.run(debug=True)
