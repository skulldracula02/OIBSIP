import importlib.util


def test_parse_intent_returns_greeting_for_hello():
    spec = importlib.util.spec_from_file_location("voice_assistant", "voice_assistant.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.parse_intent("hello there") == "greeting"


def test_parse_reminder_duration_handles_seconds():
    spec = importlib.util.spec_from_file_location("voice_assistant", "voice_assistant.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.parse_reminder_duration("remind me in 10 seconds") == 10
