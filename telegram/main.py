import os
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bots.test_bot import start, help_command, echo, set_web_agent, set_chat_agent, llm_list, change_llm, agent_list
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


if __name__ == "__main__":
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("llm_list", llm_list))
    application.add_handler(CommandHandler("change_llm", change_llm))
    application.add_handler(CommandHandler("agent_list", agent_list))
    application.add_handler(CommandHandler("set_web", set_web_agent))
    application.add_handler(CommandHandler("set_chat", set_chat_agent))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
