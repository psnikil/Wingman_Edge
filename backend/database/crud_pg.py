"""
CRUD operation are written in this helper file
This file holds all the operation/functions performed on the database
"""

from sqlalchemy.orm import Session
from backend.database.db_models import Chat_db,Message_db


# Add chat
def add_chat(session:Session,chat:Chat_db): #similar to create chat
    session.add(chat)
    session.commit()
    session.refresh(chat)

    return chat

def get_chat(session:Session,chat_id:str):
    print('the chat id recieved in crud is',chat_id)
    return session.query(Chat_db).filter(Chat_db.chatId == chat_id).first()

def get_allchats(session:Session):
    return session.query(Chat_db).all()

# TODO: need to type check the updates
def update_chat(session:Session, chat_id:str, updates: dict):
    chat = get_chat(session,chat_id)
    db_chat_updates = updates.__dict__
    for key,value in db_chat_updates.items():
        setattr(chat,key,value)
    session.commit()
    return chat

def delete_chat(session:Session,chat_id:str):
    chat = get_chat(session,chat_id)
    session.delete(chat)
    session.commit()


def add_message(session:Session,message:Message_db):
    session.add(message)
    session.commit()
    session.refresh(message)

# get the messages of a chat given its chat id
def get_messages(session:Session,chat_id:str):
    return session.query(Message_db).filter(Message_db.chatId == chat_id).all()
    
# TODO: need to type check the updates
def update_message(session:Session,message_id:str,updates: dict):
    message = get_messages(session,message_id)
    for key,value in updates.items():
        setattr(message,key,value)
    session.commit()
    return message
