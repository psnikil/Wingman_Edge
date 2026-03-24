from backend.app.schemas.misc import IsInit
from fastapi import Depends
# from app.schemas.chat import Chat, Message, Prompt
from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running, start_ollama, list_ollama_models
import uuid
from datetime import datetime
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, Session
# from app.infrastructure.database.db_models import Chat_db, Base,Message_db
# from app.infrastructure.database.crud import add_chat, get_chat, update_chat, get_allchats,add_message, get_messages
# from typing import List
# import re

# DATABASE_URL = "postgresql://nikilps:Admin123@localhost:6969/wingman_db"
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(bind=engine)

# # Global chats dictionary to persist for server lifetime
# # chats = {}  # Dict[str, Chat]
# chat_cache = () #Tuple[str,Chat]

# # Dependency for session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


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
        

# """ Function only creates the chat and returns the chatID. Messages are not added here """
# class ChatService:
#     def __init__(self):
#         pass

#     def create_chat(self, db:Session, userPrompt='' )->str:
#         global chat_cache
#         chat_id = str(uuid.uuid4())
#         if userPrompt:
#             chat_name = f"New Chat: {userPrompt[:6]}"
#             chat_summary = userPrompt[:12]
#         else:
#             chat_name = "New Chat"
#             chat_summary = 'No Messages!!!!'

#         created_at = datetime.now()
#         updated_at = datetime.now()
#         chat = Chat(
#             chatId=chat_id,
#             chatName=chat_name,
#             chatSummary=chat_summary,
#             messages=[],
#             createdAt=created_at,
#             updatedAt=updated_at
#         )
#         # Adding to database
#         try:
#             new_chat = Chat_db(**chat.__dict__)
#             add_chat(db,new_chat)
#         except Exception as e:
#             print('There was an error adding chat to database',e)

#         return chat_id
    
#     def get_chat_byID(self, chatId, db: Session)->Chat:
#         global chat_cache
#         """ Retrieve chat by ID if given else raise error """
        
#         print('the chat id in services is',chatId)
#         try:
#             chat_db = get_chat(session=db, chat_id=chatId)
#             messages_db = get_messages(session=db, chat_id=chatId)
#             messages = [Message(**message.__dict__) for message in messages_db]
#             l_chat = Chat(**chat_db.__dict__,messages=messages)
#             print(f'2:The chat got by the ID {chatId} is {l_chat}')

#             return l_chat
#         except Exception as e:
#             print(f'there was an error retrieving chat with the ID {chatId} and error is {e}')
#             raise ValueError(f"Error getting chat with ID {chatId} amd error is {e}")
    
#     def get_all_chats(self,db: Session):
#         """
#         Return all chats as list of dicts (serialized for frontend)
#         TODO: add pagination and sorting
#         """

#         all_chats = get_allchats(db)
#         print('the value of all chats in services is',all_chats)
#         if not all_chats:
#             print('There are no chats in the db currently')
#             return []
#         return all_chats
    
#     def get_messages(self, chatId, db: Session):
#         global chat_cache

#         try:
            
#             messages = get_messages(session=db, chat_id=chatId)

#             return messages
#         except Exception as e:
#             print(f'there was an error getting the chat message due to: {e}')
#             raise e

    
#     """ TODO: The adding of messages can be consolidated into a single method if needed """

#     def add_user_message(self, chatId, prompt:Prompt,db: Session):
#         global chat_cache
#         print('the chat cache in add_user_message is ',chat_cache)
#         chat = self.get_chat_byID(chatId,db) #remove, to get from database

#         try:
#             if len(chat.messages) > 1:
#                 context = UtilServices.build_context_from_history(chat.messages)
#             else:
#                 context = ''
#             # Add user prompt
#             user_msg = Message(messageId=str(uuid.uuid4()), content=prompt.message, role='user', timestamp=datetime.now())
#             chat.messages.append(user_msg)
#             print('the context for the chat is',context, 'and the model is',prompt.model)
#             # db type
#             # TODO: need to find a neater way to pass user_msg rather than this primitive type caste
#             new_user_message = Message_db(**user_msg.__dict__,chatId=chatId)
#             _ = add_message(db, new_user_message)
#             chat.updatedAt = user_msg.timestamp
#             if not prompt.model:
#                 raise "There is no LLM selected"
            
            
#             # Generate response and add to chat
#             llm_reply = generate_llm_response(prompt.message, prompt.model, context) #TODO: create a function to create context from messages
#             assistant_msg = Message(messageId=str(uuid.uuid4()), content=llm_reply, role='assistant', timestamp=datetime.now())
#             print(f"Generated response: {llm_reply}")
#             chat.messages.append(assistant_msg)
#             new_llm_message = Message_db(**assistant_msg.__dict__,chatId=chatId)
#             _ = add_message(db, new_llm_message)
#             chat.updatedAt = user_msg.timestamp


#             # update the cache
#             print('Updated the cache')
#             # chat_cache = UtilServices.update_cache(chatId,chat,messages=chat.messages)

#             # chats[chatId] = chat
#             return assistant_msg
#         except Exception as e:
#             print("There was an error in adding the user message",e)
#             raise e
        
#     @DeprecationWarning
#     def add_assistant_message(self, chatId, content:Prompt):
#         global chat_cache
#         if chat_cache and chat_cache[0] == chatId:
#             print('got data from chat cache')            
#             chat = chat_cache[1]
#         else:
#             print('had to search for data :(')
#             chat = self.get_chat_byID(chatId) #remove, to get from database
        
#         msg_id = str(uuid.uuid4())
#         timestamp = datetime.now()
#         try:
#             msg = Message(messageId=msg_id, content=content.message, role='assistant', timestamp=timestamp)
#             chat.messages.append(msg)
#             chat.updatedAt = msg.timestamp
#             # update the cache
#             chat_cache = (chatId,chat)
#             # chats[chatId] = chat
#             return True
#         except Exception as e:
#             print("There was an error in adding the LLM message")
#             raise e

#     def get_chat_history(self, chatId,db: Session):
#         global chat_cache
#         chat = self.get_chat_byID(chatId,db) #remove, to get from database
#         return chat.messages
    
#     def update_chat_meta_data(self,chatId,userPrompt,db: Session):
#         global chat_cache
#         print('the chat cache in update_chat_meta_data is',chat_cache)
#         try:
#             chat = self.get_chat_byID(chatId,db) #remove, to get from database

#             chat_name = f"New Chat: {userPrompt[:6]}"
#             chat_summary = userPrompt[:12]
#             updated_at = datetime.now()

#             # update chat
#             chat.chatName = chat_name
#             chat.chatSummary = chat_summary
#             chat.updatedAt = updated_at

            
#             _ = update_chat(db,chatId,chat)
#             # chats[chatId] = chat
#             return True

#         except Exception as e:
#             print(f'There was an error in updating the chat',e)
#             raise e



    
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
    


    
