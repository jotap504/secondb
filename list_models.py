import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Listing models...")
try:
    for m in client.models.list():
        print(f"Name: {m.name}, Default: {m.base_model_id}")
except Exception as e:
    print(f"Error listing models: {e}")
