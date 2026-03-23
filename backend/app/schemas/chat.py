""" TODO NEED TO CONVERT THESE BASEMODELS TO MATCH THE DB CLASSES """

from pydantic import BaseModel
from datetime import datetime
from typing import List

class Message(BaseModel):
    messageId: str = ""
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    llm:str
    

class Chat(BaseModel):
    chatId: str
    chatName: str
    chatSummary:str
    messages: List[Message]
    createdAt: datetime
    updatedAt: datetime

class CreateChatRequest(BaseModel):
    userPrompt: str = ""
    model:str = ''

class ChatRequest(BaseModel):
    chatId: str
    prompt: str
    model: str = ''  # Optional, can be used to specify which LLM to use
    

class ChatResponse(BaseModel):
    chatId: str #not sure we need to send back chatID in response
    message: Message

#This is the type when request a new chat window
class ChatDataResponse(BaseModel):
    chatId: str
    messages: List[Message] = []
    

class Prompt(BaseModel):
    message:str
    model:str

class UpdateChat(BaseModel):
    chatId:str
    prompt:str

class config:
    orm_mode = True


