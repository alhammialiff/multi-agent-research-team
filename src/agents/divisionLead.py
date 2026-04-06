from typing import Literal, TypedDict


from dotenv import load_dotenv
import os
from typing import Annotated, Dict, List, Optional

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import HumanMessage
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


def makeDivisionLead(llm: BaseChatModel, members: List[str]) -> str:

    """ A function to instantiate a Division Lead node """
    options = ["FINISH"] + members
    systemPrompts = (
        f"You are the division lead for two teams: {members}"
        " Given the following user request, decide which team you should work on the request."
        " You should review outputs from each team, and decide if it is good enough to progress to"
        " the next steps. Finally, you will decide if the final result is good enough as the final response."
        " When finished, respond with FINISH"
    )

    class Router(TypedDict):

        next: Literal[*options]

    def divisionLead(state: State) -> Command[Literal[*members, "__end__"]]:

        # Define message with its Role, Instructions, and State
        messages = [
            {"role": "system", "content":systemPrompts}
        ] + state["messages"]

        # Use Router type to structure response
        response = llm.with_structured_output(Router).invoke(messages)
        
        # Define where should it pipe its output to (Next agent, or END?)
        goto = response["next"]

        if goto == "FINISH":
            goto = END

        # Handoff control to another agent
        return Command(
            goto=goto,
            update={
                "messages": state["messages"] + [
                    HumanMessage(content=f"Division lead selected {goto}", name="divisionLead")             
                ]
            }
        )
    
    return divisionLead