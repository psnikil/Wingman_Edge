import re
import os
import shutil
import time
from contextlib import contextmanager
from typing import Generator, List
# from app.schemas.chat import Chat, Message, Prompt
from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running, start_ollama, list_ollama_models
from backend.app.schemas.misc import IsInit
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.schemas.chat import Chat, Message, Prompt
from backend.database.db_models import Chat_db, Base,Message_db
from backend.database.crud_pg import add_chat, get_chat, update_chat, get_allchats,add_message, get_messages
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def ensure_database_schema() -> None:
    """Create tables from ORM metadata if they are missing (safe to call on every startup)."""
    Base.metadata.create_all(bind=engine)



# Dependency for session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def _chat_session(db: Session | None) -> Generator[Session, None, None]:
    """Use caller session if provided; otherwise open/close SessionLocal."""
    if db is not None:
        yield db
    else:
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()


# class UtilServices:       
#     def __init__(self):
#         pass

#     def clean_think_tags(text: str) -> str:
#         """Remove <think>...</think> tags and their content from the response."""
#         return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

#     def build_context_from_history(messages: list[Message])->str:

#         formatted_messages = []

#         print('The chat received to build context is', messages)

#         for msg in messages:
#             role_label = "User" if msg.role == "user" else "Assistant"
#             timestamp_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
#             formatted_messages.append(f"[{timestamp_str}] {role_label}: {UtilServices.clean_think_tags(msg.content)}")
        
#         return "\n".join(formatted_messages)
    
#     def update_cache(self,chatId,chat:Chat,messages:List[Message]=[]):
#         print(f'the chat messages in chat are {chat.messages} and db messages are {messages}')
#         chat.messages = messages
#         updated_chat = Chat(**chat.__dict__)
#         chat_cache = (chatId,updated_chat)
#         return chat_cache
        

""" Function only creates the chat and returns the chatID. Messages are not added here """
class ChatService:
    def __init__(self):
        pass

    def create_chat(self, chat_id: str, userPrompt: str = "", db: Session | None = None) -> str:
        effective_id = (chat_id or "").strip() or str(uuid.uuid4())
        if userPrompt:
            chat_name = f"New Chat: {userPrompt[:6]}"
            chat_summary = userPrompt[:12]
        else:
            chat_name = "New Chat"
            chat_summary = "No Messages!!!!"

        chat = Chat(
            chatId=effective_id,
            chatName=chat_name,
            chatSummary=chat_summary,
            messages=[],
        )
        with _chat_session(db) as s:
            try:
                new_chat = Chat_db(**chat.__dict__)
                add_chat(s, new_chat)
            except Exception as e:
                print("There was an error adding chat to database", e)
                raise

        return effective_id

    def get_chat_byID(self, chat_id: str, db: Session | None = None) -> Chat | None:
        """Return chat by ID, or None if missing."""
        print("the chat id in services is", chat_id)
        with _chat_session(db) as s:
            try:
                chat_db = get_chat(chat_id=chat_id, session=s)
                if chat_db is None:
                    return None
                messages_db = get_messages(chat_id=chat_id, session=s)
                messages = [Message(**message.__dict__) for message in messages_db]
                l_chat = Chat(**chat_db.__dict__, messages=messages)
                print(f"2:The chat got by the ID {chat_id} is {l_chat}")
                return l_chat
            except Exception as e:
                print(f"there was an error retrieving chat with the ID {chat_id} and error is {e}")
                raise ValueError(
                    f"Error getting chat with ID {chat_id} and error is {e}"
                ) from e

    def get_all_chats(self, db: Session | None = None) -> List[Chat]:
        """
        Return all chats as list of dicts (serialized for frontend)
        TODO: add pagination and sorting
        """
        with _chat_session(db) as s:
            all_chats = get_allchats(s)
            print("the value of all chats in services is", all_chats)
            if not all_chats:
                print("There are no chats in the db currently")
                return []
            return all_chats

    def get_messages(self, chatId: str, db: Session | None = None) -> List[Message]:
        with _chat_session(db) as s:
            try:
                return get_messages(session=s, chat_id=chatId)
            except Exception as e:
                print(f"there was an error getting the chat message due to: {e}")
                raise

    """ TODO: The adding of messages can be consolidated into a single method if needed """

    def add_chat_message(
        self, chat_id: str, message: Message, db: Session | None = None
    ) -> bool:
        with _chat_session(db) as s:
            try:
                new_msg = Message(
                    messageId=str(uuid.uuid4()),
                    content=message.content,
                    role=message.role,
                    timestamp=datetime.now(),
                )
                new_user_message = Message_db(**new_msg.__dict__, chatId=chat_id)
                _ = add_message(s, new_user_message)
            except Exception as e:
                print("There was an error in adding the user message", e)
                raise

        return True

    def get_chat_history(self, chatId: str, db: Session | None = None) -> List[Message]:
        chat = self.get_chat_byID(chatId, db)
        if chat is None:
            return []
        return chat.messages

    def update_chat_meta_data(
        self, chatId: str, userPrompt: str, db: Session | None = None
    ) -> bool:
        with _chat_session(db) as s:
            try:
                chat = self.get_chat_byID(chatId, s)
                if chat is None:
                    return False

                chat_name = f"New Chat: {userPrompt[:6]}"
                chat_summary = userPrompt[:12]
                updated_at = datetime.now()

                chat.chatName = chat_name
                chat.chatSummary = chat_summary
                chat.updatedAt = updated_at

                _ = update_chat(s, chatId, chat)
                return True

            except Exception as e:
                print("There was an error in updating the chat", e)
                raise



    
class IsInitService:
    def __init__(self):
        # Start with isInit set to False
        self.is_init = False

    def update_init(self, status: bool):
        self.is_init = status
        return IsInit(is_init=self.is_init)


    def check_init(self):
        if not is_ollama_running():
            if shutil.which("ollama"):
                try:
                    start_ollama()
                    for _ in range(30):
                        if is_ollama_running():
                            break
                        time.sleep(0.5)
                except Exception as e:
                    print(f"❌ Error starting Ollama: {e}")
                    self.update_init(status=False)
                    return IsInit(is_init=False, err_message=str(e))
            if not is_ollama_running():
                self.update_init(status=False)
                return IsInit(
                    is_init=False,
                    err_message="Ollama is not reachable at OLLAMA_BASE_URL",
                )
            self.update_init(status=True)
            return IsInit(is_init=self.is_init)

        list_ollama_models()

        return IsInit(is_init=self.is_init)
    


    
