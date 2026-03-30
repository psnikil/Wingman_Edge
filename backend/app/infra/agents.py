import uuid
from datetime import datetime

from backend.wingman_edge_agents.agents.chat_agent import ChatAgent
from backend.wingman_edge_agents.agents.web_agent import WebAgent
from backend.app.schemas.chat import Message

from backend.app.domain.services import ChatService

# # Global chats dictionary to persist for server lifetime
# # chats = {}  # Dict[str, Chat]
# chat_cache = () #Tuple[str,Chat]

class agents_infra:

    def init_agents(self):
        self.chat_agent = ChatAgent()
        self.web_agent = WebAgent()
        self.chat_service = ChatService()

    def get_context(self, chat_id:str):
        chat = self.chat_service.get_chat_byID(chat_id)
        if chat:
            context = self.chat_service.get_chat_history(chat_id)
            return context
        return ""
        

    async def chat_agent(self, chat_id:str, model:str, query:str):

        # check if chat exists
        context = self.get_context(chat_id)
        if not context:
            
            self.chat_service.create_chat(chat_id=chat_id,userPrompt=query)
            
            agent_res = await self.chat_agent.chat_agent_af(model=model,query=query)
            agent_message = Message(messageId=str(uuid.uuid4()), content=agent_res, role='assistant', timestamp=datetime.now())

            self.chat_service.add_chat_message(chat_id=chat_id,message=agent_message,db=self.chat_service.get_db())
            return agent_res
        else:

            user_message = Message(messageId=str(uuid.uuid4()), content=query, role='user', timestamp=datetime.now())
            self.chat_service.add_chat_message(chat_id=chat_id,message=user_message,db=self.chat_service.get_db())

            agent_res = await self.chat_agent.chat_agent_af(model=model,query=query, context=context)
            agent_message = Message(messageId=str(uuid.uuid4()), content=agent_res, role='assistant', timestamp=datetime.now())

            self.chat_service.add_chat_message(chat_id=chat_id,message=agent_message,db=self.chat_service.get_db())
            return agent_res

        
    async def web_agent(self, chat_id:str, model:str, query:str):
        context = self.get_context(chat_id)
        if not context:
            self.chat_service.create_chat(chat_id=chat_id,userPrompt=query)

            agent_res = await self.web_agent.web_agent_af(model=model,query=query)

            agent_message = Message(messageId=str(uuid.uuid4()), content=agent_res, role='assistant', timestamp=datetime.now())
            self.chat_service.add_chat_message(chat_id=chat_id,message=agent_message,db=self.chat_service.get_db())

            return agent_res
        else:
            user_message = Message(messageId=str(uuid.uuid4()), content=query, role='user', timestamp=datetime.now())

            self.chat_service.add_chat_message(chat_id=chat_id,message=user_message,db=self.chat_service.get_db())
            agent_res = await self.web_agent.web_agent_af(model=model,query=query, context=context)

            agent_message = Message(messageId=str(uuid.uuid4()), content=agent_res, role='assistant', timestamp=datetime.now())
            self.chat_service.add_chat_message(chat_id=chat_id,message=agent_message,db=self.chat_service.get_db())

            return agent_res

    async def think_chat_agent(self, chat_id:str, model:str, query:str):
        context = self.get_context(chat_id)
        if not context:

            self.chat_service.create_chat(chat_id=chat_id,userPrompt=query)

            agent_res = await self.web_agent.think_web_agent_af(model=model,query=query)

            agent_message = Message(messageId=str(uuid.uuid4()), content=agent_res, role='assistant', timestamp=datetime.now())
            self.chat_service.add_chat_message(chat_id=chat_id,message=agent_message,db=self.chat_service.get_db())

            return agent_res
        else:

            user_message = Message(messageId=str(uuid.uuid4()), content=query, role='user', timestamp=datetime.now())
            self.chat_service.add_chat_message(chat_id=chat_id,message=user_message,db=self.chat_service.get_db())

            agent_res = await self.web_agent.think_web_agent_af(model=model,query=query, context=context)

            agent_message = Message(messageId=str(uuid.uuid4()), content=agent_res, role='assistant', timestamp=datetime.now())
            self.chat_service.add_chat_message(chat_id=chat_id,message=agent_message,db=self.chat_service.get_db())

            return agent_res