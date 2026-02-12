import cv2
import numpy as np

fruit_titles = {
    "orange": "Orange",
    "green_apple": "Green apple",
    "tomato": "Tomato",
    "lemon": "Lemon"
}
# to make more sensitive detector:
# adjust last value in 1st array (less Value, more sensitive)
fruit_colors = {
    fruit_titles["orange"]: [np.array([5, 150, 150]), np.array([15, 255, 255])],
    fruit_titles["green_apple"]: [np.array([40, 100, 80]), np.array([80, 255, 255])],
    fruit_titles["tomato"]: [np.array([0, 180, 120]), np.array([10, 255, 255])],
    fruit_titles["lemon"]: [np.array([20, 0, 0]), np.array([40, 255, 255])]
}
screenshot_path = "captured_image.jpg"

class Detector:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)

    def read_frame(self):
        ret, frame = self.cap.read()
        return ret, frame

    def show_frame(self, frame, elapsed_time):
        cv2.imshow("Marker Detection", frame)
        cv2.waitKey(elapsed_time)

    def screen_frame(self, frame):
        cv2.imwrite(screenshot_path, frame)

    def clean(self):
        self.cap.release()
        cv2.destroyAllWindows()


class FruitDetector(Detector):
    def __init__(self, fps):
        super().__init__()
        # number of frames per one second in milliseconds
        self.elapsed_time = int(1000/fps)
        self.first_entry_fruit = None
        self.y_text_size = 10

    def detect_fruit(self, frame, fruit_title):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        color_range = fruit_colors[fruit_title]
        mask = cv2.inRange(hsv, color_range[0], color_range[1])

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) == 0:
            self.first_entry_fruit = None
        for contour in contours:
            if cv2.contourArea(contour) > 100:
                x, y, w, h = cv2.boundingRect(contour)

                if cv2.countNonZero(mask[y:y+h, x:x+w]) > 0:
                    cv2.rectangle(frame, (x, y), (x + w, y + h),
                                  (255, 255, 255), 2)
                    self.put_text_to_frame(frame, fruit_title, (x, y-self.y_text_size))
                    if self.first_entry_fruit is None:
                        self.first_entry_fruit = (x, y)
                    height, width, channels = frame.shape
                    entry_side = "left" if self.first_entry_fruit[0] < width/2 else "right"
                    self.put_text_to_frame(frame, entry_side, (0, self.y_text_size))

    def show_frame(self, frame):
        super().show_frame(frame, self.elapsed_time)

    def put_text_to_frame(self, frame, text, coords):
        cv2.putText(frame, text, coords, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 2)
