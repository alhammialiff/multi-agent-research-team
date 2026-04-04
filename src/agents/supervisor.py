from typing import Literal, TypedDict


from dotenv import load_dotenv
import os
from typing import Annotated, Dict, List, Optional

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.tools import tool 
from langchain.chat_models import BaseChatModel

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.types import Command, Send
from langgraph.prebuilt import create_react_agent


class State(MessagesState):
    
    # The next node that it is going to hand over to
    next: str


def makeSupervisorNode(llm: BaseChatModel, members: List[str]) -> str:

    """ A function to instantiate a Supervisor node """

    options = ["FINISH"] + members
    systemPrompts = (
        "You are a supervisor tasked with managing a conversation between the" 
        f" following workers: {members}. Given the following user request," 
        " response with the worker to act next. Each worker will perform a" 
        " task and respond with their results and status. When finished," 
        " respond with FINISH."
    )

    class Router(TypedDict):
        
        next: Literal[*options]

    def supervisor(state: State) -> Command[Literal[*members, "__end__"]]:

        messages = [
            {"role": "system", "content":systemPrompts}
        ] + state["messages"]

        response = llm.with_structured_output(Router).invoke(messages)

        goto = response["next"]

        if goto == "FINISH":
            goto == END

        # Handoff control to another agent
        return Command(
            goto=goto, 
            update={"next",goto}
        )
    
    return supervisor 


