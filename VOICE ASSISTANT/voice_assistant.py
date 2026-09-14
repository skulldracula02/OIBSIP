"""A small voice assistant that also works as a text-only command-line app.

Run ``python voice_assistant.py`` for text mode, or ``python voice_assistant.py
--voice`` when a working microphone and SpeechRecognition backend are installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote_plus

COMMANDS_FILE = Path(__file__).with_name("commands.json")


def load_commands(path: Path = COMMANDS_FILE) -> dict[str, str]:
    """Load phrase-to-intent mappings, returning an empty map if unavailable."""
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        return {str(key).lower(): str(value) for key, value in data.items()}
    except (OSError, json.JSONDecodeError):
        return {}


def parse_intent(text: str, commands: Optional[dict[str, str]] = None) -> Optional[str]:
    """Return the matching intent for natural language *text*.

    Longer phrases take precedence, so ``who are you`` wins over shorter
    overlapping command phrases.
    """
    normalised = re.sub(r"\s+", " ", text.lower()).strip()
    for phrase, intent in sorted((commands or load_commands()).items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalised):
            return intent
    # Natural-language aliases that are more convenient than command labels.
    if re.search(r"\bremind\s+me\b", normalised):
        return "reminder"
    return None


def parse_reminder_duration(text: str) -> Optional[int]:
    """Extract a positive duration in seconds from phrases such as 'in 2 hours'."""
    match = re.search(r"\bin\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\b", text.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if value <= 0:
        return None
    multiplier = 1 if unit.startswith(("second", "sec")) else 60 if unit.startswith(("minute", "min")) else 3600
    return value * multiplier


def response_for_weather() -> str:
    """Fetch a no-key current-weather summary when WEATHER_CITY is configured."""
    city = os.getenv("WEATHER_CITY")
    if not city:
        return "Set WEATHER_CITY to get a weather report."
    try:
        import requests

        response = requests.get(f"https://wttr.in/{quote_plus(city)}?format=3", timeout=8)
        response.raise_for_status()
        return response.text.strip()
    except Exception:
        return "I couldn't retrieve the weather right now."


class VoiceAssistant:
    def __init__(self, speak: bool = False) -> None:
        self.speak_enabled = speak
        self._engine = None
        if speak:
            try:
                import pyttsx3

                self._engine = pyttsx3.init()
            except Exception:
                print("Text-to-speech is unavailable; continuing in text mode.")

    def say(self, message: str) -> str:
        print(f"Assistant: {message}")
        if self._engine:
            self._engine.say(message)
            self._engine.runAndWait()
        return message

    def handle(self, text: str) -> bool:
        """Handle one utterance. Return ``False`` when the session should end."""
        intent = parse_intent(text)
        if intent == "greeting":
            self.say("Hello! How can I help?")
        elif intent == "time":
            self.say(datetime.now().strftime("It is %H:%M."))
        elif intent == "date":
            self.say(datetime.now().strftime("Today is %A, %d %B %Y."))
        elif intent == "identity":
            self.say("I am your voice assistant.")
        elif intent == "search":
            query = re.sub(r"^.*?\bsearch(?:\s+for)?\s*", "", text, flags=re.I).strip()
            if not query:
                self.say("What should I search for?")
            else:
                webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
                self.say(f"Searching for {query}.")
        elif intent == "weather":
            self.say(response_for_weather())
        elif intent == "reminder":
            seconds = parse_reminder_duration(text)
            if seconds is None:
                self.say("Please say a duration, for example: remind me in 10 minutes.")
            else:
                message = re.sub(r"^.*?\b(?:to\s+)?", "", text, count=1).strip() or "Reminder"
                threading.Timer(seconds, lambda: self.say(f"Reminder: {message}")).start()
                self.say(f"Okay, I'll remind you in {seconds} seconds.")
        elif intent == "email":
            self.say("Email sending needs to be connected to an email provider first.")
        elif intent == "exit":
            self.say("Goodbye!")
            return False
        else:
            self.say("I didn't understand that. Try hello, time, date, search, weather, reminder, or exit.")
        return True


def listen() -> str:
    """Capture one spoken command using the default microphone."""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)
    return recognizer.recognize_google(audio)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple voice assistant")
    parser.add_argument("--voice", action="store_true", help="listen through the default microphone")
    parser.add_argument("--speak", action="store_true", help="read replies aloud")
    args = parser.parse_args()
    assistant = VoiceAssistant(speak=args.speak)
    assistant.say("Voice assistant ready. Type a command or say one aloud.")

    running = True
    while running:
        try:
            command = listen() if args.voice else input("You: ")
            print(f"You: {command}" if args.voice else "", end="")
            running = assistant.handle(command)
        except (EOFError, KeyboardInterrupt):
            assistant.say("Goodbye!")
            break
        except Exception as error:
            assistant.say(f"I couldn't understand that ({error}). Please try again.")


if __name__ == "__main__":
    main()
