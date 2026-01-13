import os
import asyncio
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from threading import Lock
from typing import Optional

import database
import generate_dashboard
from ai import analyze_message

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Global lock to prevent concurrent dashboard generations
dashboard_lock = Lock()

# Allowed users from env (will use the first one as default for web if not specified)
ALLOWED_USERS = [int(i.strip()) for i in os.getenv("ALLOWED_USER_IDS", "").split(",") if i.strip()]
DEFAULT_USER_ID = ALLOWED_USERS[0] if ALLOWED_USERS else 0

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Trigger initial dashboard generation
    logging.info("Triggering initial dashboard generation on startup...")
    try:
        await generate_dashboard.generate_dashboard_file_async()
        logging.info("Initial dashboard generation complete.")
    except Exception as e:
        logging.error(f"Failed initial dashboard generation: {e}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    if not os.path.exists("dashboard.html"):
        return "El dashboard se está generando. Por favor, refresca en unos segundos..."
    return FileResponse("dashboard.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_alias():
    return await get_dashboard()

@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(...),
    user_id: int = Form(DEFAULT_USER_ID),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    logging.info(f"Received message from web user {user_id}: {message[:50]}...")
    
    image_data = None
    if image:
        logging.info(f"Received image: {image.filename}")
        image_data = await image.read()
    
    audio_data = None
    if audio:
        logging.info(f"Received audio: {audio.filename}")
        audio_data = await audio.read()
    
    try:
        logging.info("Calling analyze_message...")
        try:
            response_text = await asyncio.wait_for(
                analyze_message(message, image_data, audio_data),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            logging.error("AI analysis timed out after 45 seconds")
            return {"response": "Lo siento, la IA tardó demasiado en responder. Intenta de nuevo.", "category": "OTHER"}
            
        logging.info(f"analyze_message returned: {response_text[:100]}...")
        
        # Cleanup of code blocks if AI returns markdown json
        clean_response = response_text.replace("```json", "").replace("```", "").strip()
        
        try:
            ai_data = json.loads(clean_response)
            category = ai_data.get("category")
            data = ai_data.get("data", {})
            confirmation = ai_data.get("response", "Hecho.")

            if category == "EXPENSE":
                amount = (data.get("amount") or data.get("monto") or data.get("value") or 0)
                description = (data.get("description") or data.get("descripcion") or "No description")
                currency = (data.get("currency") or data.get("moneda") or "USD")
                await database.add_expense(user_id=user_id, amount=float(amount), description=description, currency=currency)

            elif category == "TASK":
                description = (data.get("description") or data.get("descripcion") or "No description")
                deadline = (data.get("when") or data.get("fecha") or data.get("deadline"))
                await database.add_task(user_id=user_id, description=description, deadline=deadline)

            elif category == "NOTE":
                content = (data.get("content") or data.get("contenido") or message)
                await database.add_note(user_id=user_id, content=content)
            
            # Regenerate Dashboard in a non-blocking way
            async def run_dashboard_async():
                if dashboard_lock.acquire(blocking=False):
                    try:
                        logging.info("Starting background dashboard regeneration...")
                        await generate_dashboard.generate_dashboard_file_async()
                    except Exception as e:
                        logging.error(f"Error regenerating dashboard: {e}")
                    finally:
                        dashboard_lock.release()
            
            asyncio.create_task(run_dashboard_async())
            
            return {"response": confirmation, "category": category}

        except json.JSONDecodeError:
            logging.warning(f"Failed to decode AI response as JSON: {clean_response}")
            return {"response": clean_response, "category": "OTHER"}

    except Exception as e:
        logging.error(f"Error in chat_endpoint: {e}", exc_info=True)
        return {"response": f"Hubo un error interno: {str(e)}", "category": "OTHER"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
