import cv2
from image_detector import FruitDetector, fruit_titles

detector = FruitDetector(30)

while True:
    ret, frame = detector.read_frame()
    if ret is None:
        print("Camera Error")
        break

    detector.detect_fruit(frame, fruit_titles["orange"])

    detector.show_frame(frame)

detector.clean()
