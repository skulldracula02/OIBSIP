# Voice Assistant

A lightweight personal assistant that accepts typed commands and can optionally
use a microphone and text-to-speech.

## Setup

```powershell
python -m pip install -r requirements.txt
```

Audio microphone support may additionally require PyAudio for your platform.

## Run

```powershell
python voice_assistant.py
python voice_assistant.py --voice --speak
```

Set a city before asking for weather:

```powershell
$env:WEATHER_CITY = "Johannesburg"
```

Supported commands include `hello`, `time`, `date`, `search for ...`,
`weather`, `remind me in 10 minutes`, `who are you`, and `exit`.

## Test

```powershell
python -m pytest -q
```
