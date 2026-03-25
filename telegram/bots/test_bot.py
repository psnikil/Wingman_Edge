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

import httpx

history=[]
turn=0
agent = "chat_agent"

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_CHAT_ID = os.getenv("TELEGRAM_BOT_CHAT_ID")
URL="http://localhost:8000"
CHAT_LLM = os.getenv("CHAT_LLM")


client = httpx.AsyncClient()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    response = await client.get(f"{URL}/is_init")

    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Send me a message and I’ll answer with an LLM. the response for init is {response.json()}",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    help_text = (
        "<b>Wingman Edge Bot Help</b>\n\n"
        "Just send any text to chat with the current LLM and agent.\n\n"
        "<b>Commands:</b>\n"
        "/start - Initialize the connection\n"
        "/help - Show this help message\n\n"
        "<b>Model Management:</b>\n"
        "/llm_list - List available models on Ollama\n"
        "/change_llm &lt;model_name&gt; - Change the current LLM model\n\n"
        "<b>Agent Management:</b>\n"
        "/agent_list - List available agents\n"
        "/set_web - Switch to Web Agent (can search the web)\n"
        "/set_chat - Switch to Chat Agent (standard interaction)\n\n"
        "<b>Status:</b>\n"
        f"Current Model: <code>{CHAT_LLM}</code>\n"
        f"Current Agent: <code>{agent}</code>"
    )
    await update.message.reply_html(help_text)


async def llm_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available LLMs from Ollama."""
    try:
        response = await client.get(f"{URL}/list_ollama_models")
        if response.status_code == 200:
            models = response.json()
            if not models:
                await update.message.reply_text("No models found on Ollama.")
            else:
                formatted_models = "\n".join([f"• `{m}`" for m in models])
                await update.message.reply_text(f"Available LLMs:\n{formatted_models}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"Failed to fetch models. Status: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Error fetching models: {str(e)}")


async def change_llm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change the current LLM model after validating it against available models."""
    global CHAT_LLM
    if not context.args:
        await update.message.reply_text("Please provide a model name.\nUsage: `/change_llm llama3`", parse_mode="Markdown")
        return
    
    new_model = context.args[0]
    
    try:
        # Fetch available models to validate
        response = await client.get(f"{URL}/list_ollama_models")
        if response.status_code == 200:
            available_models = response.json()
            if new_model in available_models:
                CHAT_LLM = new_model
                await update.message.reply_text(f"✅ LLM successfully changed to: `{CHAT_LLM}`", parse_mode="Markdown")
            else:
                formatted_models = "\n".join([f"• `{m}`" for m in available_models])
                await update.message.reply_text(
                    f"❌ Model `{new_model}` is not available.\n\n"
                    f"Please choose from the following available models:\n{formatted_models}",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(f"⚠️ Failed to validate model. Status: {response.status_code}. Please try again later.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error validating model: {str(e)}")


async def agent_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available agents."""
    agents = ["chat_agent", "web_agent"]
    formatted_agents = "\n".join([f"• `{a}`" for a in agents])
    await update.message.reply_text(f"Available Agents:\n{formatted_agents}\n\nUse `/set_web` or `/set_chat` to switch.", parse_mode="Markdown")

async def set_web_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global agent
    agent="web_agent"
    await update.message.reply_text("Agent set to `web_agent`", parse_mode="Markdown")

async def set_chat_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global agent
    agent="chat_agent"
    await update.message.reply_text("Agent set to `chat_agent`", parse_mode="Markdown")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond with the user message with LLM"""
    global history,turn,agent
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    payload ={
        "model":CHAT_LLM,
        "query":user_text,
        "chatId":"1",
    }
    try:
        await update.message.chat.send_action("typing")
        print('The agent is ', agent)
        if "chat_agent" == agent:
            # using REST API
            response = await client.post(f"{URL}/chat", json=payload)
            print("The response is: ", response)
            ai_reply = response.json()
        elif "web_agent" == agent:
            # using REST API
            response = await client.post(f"{URL}/web_agent", json=payload)
            print("The response is: ", response)
            ai_reply = response.json()
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
    application.add_handler(CommandHandler("llm_list", llm_list))
    application.add_handler(CommandHandler("change_llm", change_llm))
    application.add_handler(CommandHandler("agent_list", agent_list))
    application.add_handler(CommandHandler("set_web", set_web_agent))
    application.add_handler(CommandHandler("set_chat", set_chat_agent))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()