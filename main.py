import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from backend.app.api.v1 import inits_api, chat_api, ollama_api
from backend.telegram.bots.test_bot import start,help_command,echo,set_agent,set_chat_agent
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
APP_HOST = os.getenv("APP_HOST","0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT","8000"))

app = FastAPI(
    title="Wingman Agent on the Edge",
    description="Backend for managing Ollama models and LangGraph agents on the Rasp Pi.",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ollama_api.router, tags=["ollama"])
app.include_router(chat_api.router, tags=["chat"])
app.include_router(inits_api.router, tags=["init"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Wingman Agent on the Edge API"}


if __name__ == "__main__":
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("set_agent", set_agent))
    application.add_handler(CommandHandler("set_chat", set_chat_agent))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    
    # print(f"Starting server on {APP_HOST}:{APP_PORT}")
    # uvicorn.run(app, host=APP_HOST, port=APP_PORT)
