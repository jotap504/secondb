import os
import logging
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from groq import AsyncGroq
from dotenv import load_dotenv
import asyncio
import json

load_dotenv()

# --- Configuración OpenRouter (OpenAI SDK Compatible) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
) if OPENROUTER_API_KEY else None
# Usamos un modelo que NO sea Gemini para evitar los mismos límites de Google
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# --- Configuración Groq (Groq SDK) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Configuración Gemini (Google SDK) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_INSTRUCTION = """
Eres un asistente de IA para una aplicación de gestión de vida. 
Tu objetivo es categorizar la entrada del usuario en una de estas categorías:
- EXPENSE: Gasto de dinero (monto, descripción, fecha, moneda).
- TASK: Algo que hacer (descripción, fecha límite si existe).
- NOTE: Información general o pensamiento (contenido).
- PLANNING: Una meta o proyecto grande que necesita desglose.
- OTHER: Cualquier otra cosa (saludo, pregunta, incierto).

IMPORTANTE: Responde SIEMPRE en ESPAÑOL.

Salida: JSON válido en este formato exacto:
{
    "category": "EXPENSE" | "TASK" | "NOTE" | "PLANNING" | "OTHER",
    "data": { ... campos relevantes ... },
    "response": "Un mensaje corto y amigable de confirmación en español"
}
"""

async def analyze_message_openrouter(text: str):
    """Llamada usando OpenRouter (Prioridad 1)."""
    if not openrouter_client:
        raise ValueError("OpenROUTER API Key no configurada")

    logging.info(f"Intentando con OpenRouter ({OPENROUTER_MODEL})...")
    response = await openrouter_client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": text}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def analyze_message_groq(text: str):
    """Llamada usando Groq (Prioridad 2)."""
    if not groq_client:
        raise ValueError("Groq API Key no configurada")

    logging.info(f"Fallback 1: Intentando con Groq ({GROQ_MODEL})...")
    response = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": text}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def analyze_message_gemini(text: str, image_data: bytes = None, audio_data: bytes = None):
    """Llamada usando el SDK oficial de Google GenAI (Prioridad 3)."""
    if not gemini_client:
        raise ValueError("Gemini API Key no configurada")

    content_parts = []
    if text: content_parts.append(text)
    if image_data:
        content_parts.append(types.Part.from_bytes(data=image_data, mime_type="image/jpeg"))
    if audio_data:
        content_parts.append(types.Part.from_bytes(data=audio_data, mime_type="audio/ogg"))

    generate_config = types.GenerateContentConfig(
        temperature=0.4,
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json"
    )

    logging.info(f"Fallback 2: Intentando con directo Gemini ({GEMINI_MODEL})...")
    response = await gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=content_parts,
        config=generate_config
    )
    return response.text

async def analyze_message(text: str, image_data: bytes = None, audio_data: bytes = None):
    """Gestor principal con OpenRouter como prioridad."""
    
    # Si hay imagen o audio, vamos directo a Gemini porque es el que mejor lo soporta
    if image_data or audio_data:
        try:
            return await analyze_message_gemini(text, image_data, audio_data)
        except Exception as e:
            logging.error(f"Gemini multimodal falló: {e}")
            return json.dumps({"category": "OTHER", "data": {}, "response": "Error: No pude procesar el archivo multimedia."})

    # 1. Intentar con OpenRouter (Primary)
    if openrouter_client:
        try:
            return await analyze_message_openrouter(text)
        except Exception as or_e:
            logging.error(f"OpenRouter falló: {or_e}")

    # 2. Intentar con Groq (Fallback 1)
    if groq_client:
        try:
            return await analyze_message_groq(text)
        except Exception as groq_e:
            logging.error(f"Groq falló: {groq_e}")

    # 3. Intentar con Gemini Directo (Fallback 2)
    if gemini_client:
        try:
            return await analyze_message_gemini(text)
        except Exception as e:
            logging.warning(f"Gemini directo falló: {e}")

    # Fallback final
    error_msg = "Lo siento, mis servicios de IA están saturados en este momento. Por favor, intenta de nuevo en unos minutos."
    return json.dumps({
        "category": "OTHER",
        "data": {},
        "response": error_msg
    })
