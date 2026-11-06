import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Camera not detected")
    exit()

with mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh:

    while True:
        success, frame = cap.read()

        if not success:
            print("Camera frame unavailable")
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            print("FACE DETECTED")
            for face in results.multi_face_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    frame,
                    face,
                    mp_face_mesh.FACEMESH_CONTOURS
                )
        else:
            print("NO FACE")

        cv2.imshow("FocusForge - FaceMesh Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()