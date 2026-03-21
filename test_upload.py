
import requests

url = "http://localhost:8000/api/v1/resumes"
data = {
    "type": "Test script",
    "format": "pdf",
    "initial_latex": ""
}
files = {
    "file": ("test.pdf", b"%PDF-1.4...", "application/pdf")
}

# Add a dummy auth header if needed, but let's see the 422 first
response = requests.post(url, data=data, files=files)
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")
