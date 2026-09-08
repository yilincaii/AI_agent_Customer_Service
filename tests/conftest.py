import os

# Test-only placeholders; no real .env exists in this snapshot.
for name, value in {
    "CHAT_MODEL": "test-model", "CHAT_BASE_URL": "https://model.example/v1",
    "CHAT_API_KEY": "test-placeholder", "CHAT_THINKING": "",
    "CHAT_REASONING_EFFORT": "", "CHAT_REASONING_SPLIT": "",
}.items():
    os.environ[name] = value
