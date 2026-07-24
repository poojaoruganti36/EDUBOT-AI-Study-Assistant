import speech_recognition as sr
import pyttsx3


def get_voice_input() -> str:
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        return recognizer.recognize_google(audio)
    except Exception:
        return ""


def speak(text: str) -> None:
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        return
