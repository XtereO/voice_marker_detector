import json
import queue
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional

import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer

MODEL_PATH = "vosk-model-small-ru-0.22"
SAMPLE_RATE = 16000

class Speaker:
    def __init__(self) -> None:
        self.rate = 175
        self.volume = 1.0
        self._init_engine()

    def _init_engine(self):
        # Pick a backend explicitly
        if sys.platform.startswith("win"):
            self.engine = pyttsx3.init(driverName="sapi5")
        elif sys.platform == "darwin":
            self.engine = pyttsx3.init(driverName="nsss")
        else:
            self.engine = pyttsx3.init(driverName="espeak")

        self.engine.setProperty("rate", self.rate) 
        self.engine.setProperty("volume", self.volume)

    def say(self, text: str) -> None:
        print(f"[ASSISTANT] {text}")

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        finally:
            try:
                self.engine.stop()
            except Exception:
                pass

class Listener:
    def __init__(self, model_path: str, sample_rate: int = 16000) -> None:
        self.q: "queue.Queue[bytes]" = queue.Queue()
        self.sample_rate = sample_rate

        try:
            self.model = Model(model_path)
        except Exception as e:
            raise RuntimeError(
                f"Vosk model not found or failed to load: '{model_path}'.\n"
                f"Download and unzip the model folder next to this script.\n"
                f"Original error: {e}"
            ) from e

        self.rec = KaldiRecognizer(self.model, self.sample_rate)
        self.rec.SetWords(False)

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            print("[AUDIO STATUS]", status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen_text(self, timeout_s: float = 8.0) -> Optional[str]:
        """
        Listen to microphone and return one recognized phrase (best effort).
        Returns None on timeout.
        """
        start = time.time()

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._callback,
        ):
            while True:
                if time.time() - start > timeout_s:
                    return None

                try:
                    data = self.q.get(timeout=0.2)
                except queue.Empty:
                    continue

                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = (res.get("text") or "").strip()
                    if text:
                        return text

INSTRUCTIONS = [
    "[Detect] some fruit [orange, lemon, tomato, green apple]",
    "Turn on [music] on your laptop",
    "Turn on [camera] on your laptop",
    "Make a [screenshot] on your camera",
    "[Quit]"
]
ANCHORS = {
    "detect": "detect",
    "music": "music",
    "camera": "camera",
    "screenshot": "screenshot",
    "quit": "quit"
}
COMMANDS = [
    (r"(?=.*detect)(?=.*\b(orange|apple|lemon|tomato)\b)", "Start detecting...", ANCHORS["detect"]),
    (r"(?=.*music)", "Turning on music...", ANCHORS["music"]),
    (r"(?=.*camera)", "Turning on camera...", ANCHORS["camera"]),
    (r"(?=.*screenshot)", "Say cheese...", ANCHORS["screenshot"]),
    (r"\b(quit)\b", "Goodbye.", ANCHORS["quit"]),
]

@dataclass
class CommandResult:
    handled: bool
    response: str
    should_exit: bool = False
    speak_time: bool = False
    payload: object = None
    anchor: str = None

class VoiceAssistant:
    def __init__(self):
        self.speaker = Speaker()
        self.listener = Listener(MODEL_PATH, SAMPLE_RATE)

    def greet(self):
        greeting = ";\n".join([
                    "Hello, I'm ready to assist you. I can:",
                    *INSTRUCTIONS
                    ])
        self.speaker.say(greeting)
    
    def listen_command(self, callback):
        text = self.listener.listen_text(timeout_s=10.0)
        text = text if text is not None else ""
        command_result = self.recognize_command(text)
        if(command_result.speak_time):
            self.speaker.say(command_result.response)
        else:
            print(command_result.response)
        
        callback(command_result.anchor, command_result.payload)

    def recognize_command(self, text):
        t = text.lower()

        for pattern, response, anchor in COMMANDS:
            if re.search(pattern, t):
                if anchor == ANCHORS["detect"]:
                    fruit_title = None
                    if re.search(r"\b(orange)\b"):
                        fruit_title = "orange"
                    elif re.search(r"\b(lemon)\b"):
                        fruit_title = "lemon"
                    elif re.search(r"\b(apple)\b"):
                        fruit_title = "apple"
                    elif re.search(r"\b(tomato)\b"):
                        fruit_title = "tomato"
                    if fruit_title is None:
                        break
                    return CommandResult(handled=True, response=response, speak_time=True, anchor=anchor, payload={"fruit_title": fruit_title})
                else:
                    return CommandResult(handled=True, response=response, speak_time=True, anchor=anchor)
        print("empty...")
        return CommandResult(
            handled=False,
            speak_time=False,
            response=";\n".join([
                "I misunderstand you..., I can:",
                *INSTRUCTIONS
                                 ]),
        )
    

def current_time_str() -> str:
    return time.strftime("%H:%M")

def main():
    print("=== Voice Assistant Demo (single file) ===")
    print("Wake phrase: 'привет' / 'здравствуй' / 'ассистент'")
    print("Commands: 'как дела', 'который час', 'помощь', 'выход'\n")

    speaker = Speaker()
    listener = Listener(MODEL_PATH, SAMPLE_RATE)

    awake = False

    while True:
        if not awake:
            print("[SYSTEM] Waiting for wake phrase...")
            text = listener.listen_text(timeout_s=20.0)
            if not text:
                continue

            print(f"[YOU] {text}")
            if is_wake_phrase(text):
                awake = True
                speaker.say("Привет! Я слушаю. Скажи команду.")
            else:
                print("[SYSTEM] Not a wake phrase. Try: 'привет' or 'ассистент'.")
            continue

        print("[SYSTEM] Listening for command...")
        text = listener.listen_text(timeout_s=10.0)

        if not text:
            speaker.say("Я вас не услышал. Повторите команду или скажите выход.")
            continue

        print(f"[YOU] {text}")

        result = route_command(text)
        speaker.say(result.response)

        if result.speak_time:
            speaker.say(f"Сейчас {current_time_str()}")

        if result.should_exit:
            break

        # Uncomment if you want to require wake phrase each time:
        # awake = False

    print("=== Done ===")
