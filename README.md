# AI Life OS Bot

An AI-powered personal assistant Telegram bot for tracking expenses, managing tasks, and taking notes.

## tech Stack
- **Python 3.10+**
- **python-telegram-bot**: For Telegram API interaction
- **Supabase**: For database storage
- **Google Gemini API**: For AI intelligence (OCR, NLP)

## Setup

1.  **Clone the repository** (or ensure you are in the project folder).
2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment**:
    - Copy `.env.example` to `.env`.
    - Fill in your `TELEGRAM_TOKEN` (from @BotFather).
    - Fill in your `GEMINI_API_KEY` (from Google AI Studio).
    - Fill in your `SUPABASE_URL` and `SUPABASE_KEY` (from Supabase Project Settings).
    - Add your Telegram User ID to `ALLOWED_USER_IDS` to restrict access.

## Running the Bot

```bash
python main.py
```
