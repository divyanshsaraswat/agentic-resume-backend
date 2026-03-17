import requests
import json

try:
    print("Testing local backend on http://127.0.0.1:8000/api/v1/auth/me")
    # Using a fake but realistic session cookie if possible, but just testing connectivity first
    response = requests.get("http://127.0.0.1:8000/api/v1/auth/me", timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.ConnectionError as e:
    print(f"Connection Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")
