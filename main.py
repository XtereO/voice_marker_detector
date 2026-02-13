import threading
from image_detector import FruitDetector
from voice_assistant import VoiceAssistant, ANCHORS

listening_thread_on = True
def interact_user():
    global listening_thread_on
    voice_assistant = VoiceAssistant()
    voice_assistant.greet()
    while listening_thread_on:
        voice_assistant.listen_command(react_command)

fruit_title_to_recognize = None
camera_turned = False
camera_thread_on = True
making_screenshot = False
def react_command(anchor, payload):
    global making_screenshot, camera_turned, camera_thread_on, fruit_title_to_recognize

    if anchor == ANCHORS["find"] and payload is not None:
        start_finding_fruit(payload["fruit_title"])
    elif anchor == ANCHORS["camera"]:
        start_switching_camera()
    elif anchor == ANCHORS["screenshot"]:
        start_making_screenshot()
    elif anchor == ANCHORS["quit"]:
        quit_program()

def start_finding_fruit(fruit_title):
    global camera_turned, fruit_title_to_recognize
    camera_turned = True
    fruit_title_to_recognize = fruit_title

def start_switching_camera():
    global camera_turned
    camera_turned = not camera_turned

def start_making_screenshot():
    global making_screenshot 
    making_screenshot = True

def quit_program():
    global camera_turned, camera_thread_on, listening_thread_on
    camera_turned = False
    camera_thread_on = False
    listening_thread_on = False

detector = None
def detect_fruit():
    global camera_turned, fruit_title_to_recognize, making_screenshot, detector

    while camera_turned:
        ret, frame = detector.read_frame()
        if ret is None:
            print("Camera Error")
            break
        if frame is None:
            continue

        if(fruit_title_to_recognize is not None):
            detector.detect_fruit(frame, fruit_title_to_recognize)

        if(making_screenshot):
            making_screenshot = False
            detector.screen_frame(frame)

        detector.show_frame(frame)

    detector.clean()


def interact_camera():
    global detector, camera_thread_on
    print("camera thread on", camera_thread_on)
    while camera_thread_on:
        detector = FruitDetector(30)
        detect_fruit()
    print("camera thread off")
    
if __name__ == "__main__":
    listening_thread = threading.Thread(target=interact_user)
    camera_thread = threading.Thread(target=interact_camera)
    camera_thread.start()
    listening_thread.start()
    listening_thread.join()
    camera_thread.join()
