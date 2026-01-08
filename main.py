import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import json
import threading
import http.server
import socketserver
import database
import generate_dashboard
from ai import analyze_message
from threading import Lock
import sys
import atexit

# Global lock to prevent concurrent dashboard generations
dashboard_lock = Lock()
pid_file = "bot.pid"

# Health-check server in a background thread
class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == '/dashboard':
            try:
                with open("dashboard.html", "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Dashboard not found")
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server():
    PORT = int(os.getenv("PORT", 8000))
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        logging.info(f"Serving health-check at port {PORT}")
        httpd.serve_forever()

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

# Load allowed users
ALLOWED_USERS = [int(i.strip()) for i in os.getenv("ALLOWED_USER_IDS", "").split(",") if i.strip()]

async def is_authorized(update: Update):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        logging.warning(f"Unauthorized access attempt from user_id: {user_id}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        await update.message.reply_text("Lo siento, no tienes permiso para usar este bot.")
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="¡Hola! Soy tu asistente de IA personal. Puedo ayudarte a rastrear gastos, tareas y notas. Escribe /help para ver qué puedo hacer."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
    help_text = """
    Comandos disponibles:
    /start - Iniciar el bot
    /help - Mostrar este mensaje de ayuda
    /expense <monto> <descripción> - Registrar un gasto (o envía una foto)
    /task <descripción> - Añadir una tarea
    /note <contenido> - Añadir una nota
    /remind - Ver resumen de tareas pendientes
    /update_dashboard - Actualizar el dashboard manualmente
    """
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

async def send_task_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Job callback to send reminders to all allowed users."""
    for user_id in ALLOWED_USERS:
        try:
            tasks = await database.get_pending_tasks(user_id)
            if tasks:
                message = "🔔 **Recordatorio de Tareas Pendientes:**\n\n"
                for i, task in enumerate(tasks, 1):
                    deadline = task.get("deadline")
                    date_info = f" (Vence: {deadline})" if deadline else ""
                    message += f"{i}. {task['description']}{date_info}\n"
                
                message += "\n¡Vamos! Tú puedes con esto. 💪"
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Error sending reminders to {user_id}: {e}")

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger a reminder summary."""
    if not await is_authorized(update):
        return
    await send_task_reminders(context)

async def update_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger dashboard regeneration."""
    if not await is_authorized(update):
        return
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🔄 Generando dashboard... Esto puede tomar unos segundos."
    )
    
    try:
        # Run the asynchronous dashboard generation
        await asyncio.wait_for(
            generate_dashboard.generate_dashboard_file_async(),
            timeout=30.0  # 30 second timeout
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Dashboard actualizado correctamente. Visita /dashboard para verlo."
        )
    except asyncio.TimeoutError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏱️ El dashboard tardó demasiado en generarse. Intenta de nuevo más tarde."
        )
        logging.error("Dashboard generation timed out")
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Error al generar el dashboard: {str(e)}"
        )
        logging.error(f"Error in update_dashboard_command: {e}")

if __name__ == '__main__':
    # Single instance check
    import psutil
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            if psutil.pid_exists(old_pid):
                 # Double check it's actually our python process if possible, 
                 # but for now pid_exists is better than nothing
                 print(f"Error: Bot is already running (PID: {old_pid}).")
                 sys.exit(1)
            else:
                 print("Found stale PID file. Removing...")
                 os.remove(pid_file)
        except (ValueError, FileNotFoundError, psutil.NoSuchProcess):
             if os.path.exists(pid_file):
                os.remove(pid_file)

    # Write current PID
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    def remove_pid():
        if os.path.exists(pid_file):
            os.remove(pid_file)

    atexit.register(remove_pid)

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        remove_pid()
        sys.exit(1)

    application = ApplicationBuilder().token(token).build()

    # Handlers
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help_command)
    remind_handler = CommandHandler('remind', remind_command)
    update_dashboard_handler = CommandHandler('update_dashboard', update_dashboard_command)
    
    # Generic message handler
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await is_authorized(update):
            await update.message.reply_text("Acceso denegado.")
            return
        
        user_message = update.message.text
        # Check for photo
        image_data = None
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            image_data = bytes(await photo_file.download_as_bytearray())
            user_message = update.message.caption or "Analiza esta imagen"

        # Check for voice
        audio_data = None
        if update.message.voice:
            voice_file = await update.message.voice.get_file()
            audio_data = bytes(await voice_file.download_as_bytearray())
            user_message = user_message or "Analiza este audio"

        logging.info(f"Received message from user {update.effective_user.id}: {user_message[:50]}...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            logging.info("Calling analyze_message...")
            response_text = await analyze_message(user_message, image_data, audio_data)
            logging.info("analyze_message returned.")
            
            # Simple cleanup of code blocks if Gemini returns markdown json
            clean_response = response_text.replace("```json", "").replace("```", "").strip()
            
            try:
                logging.info(f"AI Response: {clean_response[:100]}...")
                ai_data = json.loads(clean_response)
                category = ai_data.get("category")
                data = ai_data.get("data", {})
                confirmation = ai_data.get("response", "Hecho.")
                user_id = update.effective_user.id

                if category == "EXPENSE":
                    try:
                        await database.add_expense(
                            user_id=user_id,
                            amount=data.get("amount", 0),
                            description=data.get("description", "No description"),
                            currency=data.get("currency", "USD")
                        )
                    except Exception as db_e:
                        logging.error(f"Database Expense Error: {db_e}")
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al guardar gasto: {db_e}")
                        return

                elif category == "TASK":
                    try:
                        await database.add_task(
                            user_id=user_id,
                            description=data.get("description", "No description"),
                            deadline=data.get("when")
                        )
                    except Exception as db_e:
                        logging.error(f"Database Task Error: {db_e}")
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al guardar tarea: {db_e}")
                        return

                elif category == "NOTE":
                    try:
                        await database.add_note(
                            user_id=user_id,
                            content=data.get("content", user_message)
                        )
                    except Exception as db_e:
                        logging.error(f"Database Note Error: {db_e}")
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al guardar nota: {db_e}")
                        return
                
                await context.bot.send_message(chat_id=update.effective_chat.id, text=confirmation)
                
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
                    else:
                        logging.info("Dashboard generation skipped (already in progress)")

                asyncio.create_task(run_dashboard_async())
            
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                await context.bot.send_message(chat_id=update.effective_chat.id, text=clean_response)

        except Exception as e:
            logging.error(f"Error handling message: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Hubo un error al procesar tu mensaje.")

    message_handler = MessageHandler(filters.TEXT | filters.PHOTO | filters.VOICE & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(remind_handler)
    application.add_handler(update_dashboard_handler)
    application.add_handler(message_handler)

    # Start health-check server thread for Render
    threading.Thread(target=start_health_server, daemon=True).start()

    print("El bot está corriendo con recordatorios activados y servidor de salud en puerto", os.getenv("PORT", 8000))
    application.run_polling()
