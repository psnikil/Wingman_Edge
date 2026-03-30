from sqlalchemy import Column, String,DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship
import enum
from datetime import datetime
from typing import List

Base = declarative_base() #add a name for clarity, there is prolly going to be many db's so

class Role(enum.Enum):
    user = 'user'
    assistant = 'assistant'

class Chat_db(Base):
    __tablename__ = 'Chat_db'
    #TODO Make this an Index depending on create_chat procedure
    chatId = Column(String, primary_key=True, index=True) 
    chatName = Column(String)
    chatSummary = Column(String)
    # The back populate here should refer to the column name, not the table name
    messages = relationship('Message_db', back_populates='chat', cascade='all, delete-orphan')


class Message_db(Base):
    __tablename__ = 'Message_db'
    messageId = Column(String, primary_key=True, index=True)
    chatId = Column(String, ForeignKey('Chat_db.chatId'))
    role = Column(Enum(Role))
    content = Column(String)
    llm = Column(String)
    timestamp = Column(DateTime, default=datetime.now())
    tools_used = Column(String)
    # The back populate here should refer to the column name, not the table name
    chat = relationship('Chat_db', back_populates='messages')