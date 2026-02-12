import threading
import sys
from image_detector import FruitDetector, fruit_titles
from voice_assistant import VoiceAssistant, ANCHORS

def interact_user():
    voice_assistant = VoiceAssistant()
    voice_assistant.greet()
    while True:
        voice_assistant.listen_command(react_command)

def react_command(anchor, payload):
    target_to_execute = None

    match anchor:
        case ANCHORS["detect"]:
            if payload is not None:
                target_to_execute = lambda: detect_fruit(payload["fruit_title"])
            
        case ANCHORS["quit"]:
            sys.exit()

        case _:
            return
            
    
    executing_thread = threading.Thread(target=target_to_execute)
    executing_thread.start()


def detect_fruit(fruit_title):
    detector = FruitDetector(30)

    while True:
        ret, frame = detector.read_frame()
        if ret is None:
            print("Camera Error")
            break

        detector.detect_fruit(frame, fruit_titles["orange"])

        detector.show_frame(frame)

    detector.clean()

if __name__ == "__main__":
    listening_thread = threading.Thread(target=interact_user)
    listening_thread.start()
    listening_thread.join()
'''
thread1 = threading.Thread(target=callback1)
thread2 = threading.Thread(target=callback2/task2)

# Start threads
thread1.start()
thread2.start()

# Wait for both threads to complete
thread1.join()
thread2.join()'''