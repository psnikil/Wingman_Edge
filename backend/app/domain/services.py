import re
import os
from fastapi import Depends
from typing import List
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



# Dependency for session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

    def create_chat(self, db:Session, userPrompt='' )->str:
        chat_id = str(uuid.uuid4())
        if userPrompt:
            chat_name = f"New Chat: {userPrompt[:6]}"
            chat_summary = userPrompt[:12]
        else:
            chat_name = "New Chat"
            chat_summary = 'No Messages!!!!'

        created_at = datetime.now()
        updated_at = datetime.now()
        chat = Chat(
            chatId=chat_id,
            chatName=chat_name,
            chatSummary=chat_summary,
            messages=[],
        )
        # Adding to database
        try:
            new_chat = Chat_db(**chat.__dict__)
            add_chat(db,new_chat)
        except Exception as e:
            print('There was an error adding chat to database',e)

        return chat_id
    
    def get_chat_byID(self, chatId, db: Session)->Chat:
 
        """ Retrieve chat by ID if given else raise error """
        
        print('the chat id in services is',chatId)
        try:
            chat_db = get_chat(session=db, chat_id=chatId)
            messages_db = get_messages(session=db, chat_id=chatId)
            messages = [Message(**message.__dict__) for message in messages_db]
            l_chat = Chat(**chat_db.__dict__,messages=messages)
            print(f'2:The chat got by the ID {chatId} is {l_chat}')

            return l_chat
        except Exception as e:
            print(f'there was an error retrieving chat with the ID {chatId} and error is {e}')
            raise ValueError(f"Error getting chat with ID {chatId} amd error is {e}")
    
    def get_all_chats(self,db: Session):
        """
        Return all chats as list of dicts (serialized for frontend)
        TODO: add pagination and sorting
        """

        all_chats = get_allchats(db)
        print('the value of all chats in services is',all_chats)
        if not all_chats:
            print('There are no chats in the db currently')
            return []
        return all_chats
    
    def get_messages(self, chatId, db: Session):
 

        try:
            
            messages = get_messages(session=db, chat_id=chatId)

            return messages
        except Exception as e:
            print(f'there was an error getting the chat message due to: {e}')
            raise e

    
    """ TODO: The adding of messages can be consolidated into a single method if needed """

    def add_chat_message(self, chat_id:str, message:Message, db: Session):
 

        try:
            
            # Add user prompt
            new_msg = Message(messageId=str(uuid.uuid4()), content=message.content, role=message.role, timestamp=datetime.now())
            new_user_message = Message_db(**new_msg.__dict__,chatId=chat_id)
            _ = add_message(db, new_user_message)
        except Exception as e:
            print("There was an error in adding the user message",e)
            raise e
        
    def get_chat_history(self, chatId,db: Session):
 
        chat = self.get_chat_byID(chatId,db) #remove, to get from database
        return chat.messages
    
    def update_chat_meta_data(self,chatId,userPrompt,db: Session):
 
        try:
            chat = self.get_chat_byID(chatId,db) #remove, to get from database

            chat_name = f"New Chat: {userPrompt[:6]}"
            chat_summary = userPrompt[:12]
            updated_at = datetime.now()

            # update chat
            chat.chatName = chat_name
            chat.chatSummary = chat_summary
            chat.updatedAt = updated_at

            
            _ = update_chat(db,chatId,chat)
            # chats[chatId] = chat
            return True

        except Exception as e:
            print(f'There was an error in updating the chat',e)
            raise e



    
class IsInitService:
    def __init__(self):
        # Start with isInit set to False
        self.is_init = False

    def update_init(self, status: bool):
        self.is_init = status
        return IsInit(is_init=self.is_init)


    def check_init(self):

        if not is_ollama_running():
            try:
                start_ollama()
                self.update_init(status=True)
                return self.is_init
            except Exception as e:
                print(f"❌ Error starting Ollama: {e}")
                self.update_init(status=False)
                return e


        else:
            list_ollama_models()

        return IsInit(is_init=self.is_init)
    


    
