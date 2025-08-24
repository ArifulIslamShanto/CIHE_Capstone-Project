import cv2

# Load Haar cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)  # ✅ filter small detections here
    )

    for (x, y, w, h) in faces:
        # Extra check (optional, but safe)
        if w < 80 or h < 80:
            continue  

        center_coordinates = (x + w // 2, y + h // 2)
        axes_length = (int(w * 0.45), int(h * 0.60))
        cv2.ellipse(frame, center_coordinates, axes_length, 0, 0, 360, (0, 255, 0), 2)

    cv2.imshow("Face Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
