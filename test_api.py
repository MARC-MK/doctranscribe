import os
import requests
import json

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("No API key found in environment")
    exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "gpt-4.1-2025-04-14",
    "messages": [{"role": "user", "content": "Are you working now?"}],
    "max_tokens": 20
}

response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers=headers,
    data=json.dumps(data)
)

print(f"Status code: {response.status_code}")
if response.status_code == 200:
    print("Success!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error: {response.text}") 