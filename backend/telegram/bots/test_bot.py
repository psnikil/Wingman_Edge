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

from backend.wingman_edge_agents.agents.chat_agent import ChatAgent
from backend.wingman_edge_agents.agents.web_agent import WebAgent
history=[]
turn=0
agent = "chat_agent"

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

async def set_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global agent
    agent="web_agent"
    await update.message.reply_text("Agent set to web_agent")

async def set_chat_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global agent
    agent="chat_agent"
    await update.message.reply_text("Agent set to chat_agent")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond with the user message with LLM"""
    global history,turn,agent
    chat_agent = ChatAgent(provider='ollama')
    web_agent = WebAgent(provider='ollama')
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    try:
        await update.message.chat.send_action("typing")
        print('The agent is ', agent)
        if "chat_agent" == agent:
            ai_reply = await chat_agent.think_chat_llm_af(model=chat_agent.chat_llm,query=user_text, context=history)
            history.append(f"User: {user_text}")
            history.append(f"AI: {ai_reply}")
        elif "web_agent" == agent:
            ai_reply = await web_agent.web_agent_af(model=web_agent.web_llm,query=user_text, context=history)
            history.append(f"User: {user_text}")
            history.append(f"AI: {ai_reply}")
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