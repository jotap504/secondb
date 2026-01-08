
import asyncio
import os
from dotenv import load_dotenv
from ai import analyze_message

load_dotenv()

async def test():
    print("Testing AI...")
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    
    try:
        response = await analyze_message("Hola, esto es una prueba.")
        print("Response received:")
        print(response)
    except Exception as e:
        print(f"Error caught in test: {e}")

if __name__ == "__main__":
    asyncio.run(test())
