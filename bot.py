"""Telegram AI Bot — Railway-ready, OpenAI-compatible."""

import logging
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from openai import AsyncOpenAI

# ── Config ────────────────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.environ.get("MODEL", "gpt-4o-mini")
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])

# ── Logging ────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── OpenAI client ───────────────────────────────────────────────────────────────────────
ai = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# ── Conversation memory (in-memory, per user) ───────────────────────────────────
conversations: dict[int, list[dict]] = {}

SYSTEM_PROMPT = """Tu es un assistant IA expert et polyvalent. 
Tu réponds en français par défaut, de manière concise et structurée.
Tu peux analyser des URLs, rédiger, coder, et automatiser des tâches."""


# ── Handlers ────────────────────────────────────────────────────────────────────────────────
def is_allowed(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    conversations[update.effective_user.id] = []
    await update.message.reply_text(
        "U0001f916 Bot IA démarré. Envoie-moi n'importe quel message.\n"
        "Commandes : /start (réinitialiser) | /clear (vider la mémoire)"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    conversations[update.effective_user.id] = []
    await update.message.reply_text("✅ Conversation réinitialisée.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        logger.warning("Unauthorized access attempt from user %s", user_id)
        return

    user_text = update.message.text
    history = conversations.setdefault(user_id, [])

    history.append({"role": "user", "content": user_text})

    if len(history) > 20:
        history[:] = history[-20:]

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        response = await ai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=2048,
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as exc:
        logger.error("AI error: %s", exc)
        await update.message.reply_text(f"❌ Erreur : {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────────────────
def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started — polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
