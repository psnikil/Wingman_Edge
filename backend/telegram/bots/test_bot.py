import os
from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agents.util_agents import UtilAgents
history=""
turn=0

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_CHAT_ID = os.getenv("TELEGRAM_BOT_CHAT_ID")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Send me a message and I’ll answer with an LLM.",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Just send any text and I’ll respond with the LLM.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond with the user message with LLM"""
    global history,turn
    llm = UtilAgents(provider='ollama')
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    try:
        await update.message.chat.send_action("typing")
        ai_reply = llm.chat_llm_f(user_text, context=history)
        history += f"User: {user_text}\nAI: {ai_reply}\n"
        turn+=1
        print('The history is: ', history,turn)
        await update.message.reply_text(ai_reply)
    except Exception as e:
        print('LLM error', e)
        await update.message.reply_text("Sorry, something went wrong while calling the model.")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()