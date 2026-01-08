import asyncio
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY not found in environment variables")

supabase: Client = create_client(url, key)

async def add_expense(user_id: int, amount: float, description: str, currency: str = "USD"):
    data = {
        "user_id": user_id,
        "amount": amount,
        "description": description,
        "currency": currency
    }
    # Use asyncio.to_thread to run the synchronous supabase call without blocking the event loop
    response = await asyncio.to_thread(supabase.table("expenses").insert(data).execute)
    return response

async def add_task(user_id: int, description: str, deadline: str = None):
    data = {
        "user_id": user_id,
        "description": description,
        "deadline": deadline,
        "status": "pending"
    }
    response = await asyncio.to_thread(supabase.table("tasks").insert(data).execute)
    return response

async def add_note(user_id: int, content: str):
    data = {
        "user_id": user_id,
        "content": content
    }
    response = await asyncio.to_thread(supabase.table("notes").insert(data).execute)
    return response

async def get_pending_tasks(user_id: int):
    response = await asyncio.to_thread(supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute)
    return response.data
