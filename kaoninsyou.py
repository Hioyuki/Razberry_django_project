import cv2
import face_recognition
import os

class RaspberryPiCamera:
    def __init__(self):
        self.model_path = "./models"
        self.temp_image = "./detect.jpg"

    def detect_face(self):
        # 1. ????????????? (rpicam-still ????? OpenCV???)
        # ??????????????? index 0
        video_capture = cv2.VideoCapture(0)
        ret, frame = video_capture.read()
        video_capture.release()

        if not ret:
            print("[Error] ??????????????????")
            return

        # 2. ??????
        # OpenCV?BGR????face_recognition?RGB?????
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # ???????
        face_locations = face_recognition.face_locations(rgb_frame)

        if not face_locations:
            print("[Result] ????????????")
            return

        print(f"[Result] {len(face_locations)} ??????????")
        
        # 3. ???????????
        for i, (top, right, bottom, left) in enumerate(face_locations):
            print(f"Face {i+1}: top={top}, right={right}, bottom={bottom}, left={left}")

if __name__ == "__main__":
    cam = RaspberryPiCamera()
    cam.detect_face()