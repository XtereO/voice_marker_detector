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

from image_detector import fruit_titles

MODEL_PATH = "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

class Speaker:
    def __init__(self) -> None:
        self.rate = 175
        self.volume = 1.0

    def _init_engine(self):
        if sys.platform.startswith("win"):
            engine = pyttsx3.init(driverName="sapi5")
        elif sys.platform == "darwin":
            engine = pyttsx3.init(driverName="nsss")
        else:
            engine = pyttsx3.init(driverName="espeak")

        engine.setProperty("rate", self.rate) 
        engine.setProperty("volume", self.volume)
        return engine

    def say(self, text: str) -> None:
        print(f"[ASSISTANT] {text}")

        engine = self._init_engine()
        try:
            engine.say(text)
            engine.runAndWait()
        finally:
            try:
                engine.stop()
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
    "[Find] some fruit [orange, lemon, tomato, green apple]",
    "Turn on [camera] on your laptop",
    "Make a [screenshot] on your camera",
    "[Quit|Exit]"
]
ANCHORS = {
    "find": "find",
    "camera": "camera",
    "screenshot": "screenshot",
    "quit": "quit"
}
COMMANDS = [
    (r"(?=.*find)(?=.*\b(orange|apple|lemon|tomato)\b)", "Start detecting...", ANCHORS["find"]),
    (r"(?=.*camera)", "Switching camera...", ANCHORS["camera"]),
    (r"\b(screenshot|screen shot)\b", "Say cheese...", ANCHORS["screenshot"]),
    (r"\b(quit|exit)\b", "Goodbye.", ANCHORS["quit"]),
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
        greeting = "Hello, I'm ready to assist you. I can:"
        self.speaker.say(greeting)
        print(";\n".join(INSTRUCTIONS))
    
    def listen_command(self, callback):
        text = self.listener.listen_text(timeout_s=10.0)
        text = text if text is not None else ""
        print("recognized text is ", text)
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
                if anchor == ANCHORS["find"]:
                    fruit_title = None
                    if re.search(r"\b(orange)\b", t):
                        fruit_title = fruit_titles["orange"]
                    elif re.search(r"\b(lemon)\b", t):
                        fruit_title = fruit_titles["lemon"]
                    elif re.search(r"\b(apple)\b", t):
                        fruit_title = fruit_titles["green_apple"]
                    elif re.search(r"\b(tomato)\b", t):
                        fruit_title = fruit_titles["tomato"]
                    if fruit_title is None:
                        break
                    return CommandResult(handled=True, response=f"[{fruit_title}] {response}", speak_time=True, anchor=anchor, payload={"fruit_title": fruit_title})
                else:
                    return CommandResult(handled=True, response=response, speak_time=True, anchor=anchor)
        return CommandResult(
            handled=False,
            speak_time=False,
            response=";\n".join([
                "I misunderstand you..., I can:",
                *INSTRUCTIONS
                                 ]),
        )
    