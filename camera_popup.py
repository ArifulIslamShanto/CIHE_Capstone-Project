import cv2

def start_camera():
    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)  # macOS

    if not cap.isOpened():
        print("❌ Cannot open camera")
        return

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
            center = (x + w//2, y + h//2)
            axes = (w//2, int(h*0.6))  # oval
            cv2.ellipse(frame, center, axes, 0, 0, 360, (0,255,0), 2)

        cv2.imshow("Camera with Face Detection - Press 'q' to close", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_camera()
