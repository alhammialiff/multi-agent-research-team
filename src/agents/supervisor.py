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

from pydantic import BaseModel, Field


class MessageClassififer(BaseModel):
    message_type: Literal["emotional", "logical"] = Field(
        ...,
        description=""
    )

class State(MessagesState):
    
    # The next node that it is going to hand over to
    next: str

    # Message types 
    message_types: str | None


def makeSupervisorNode(llm: BaseChatModel, members: List[str]) -> str:

    """ A function to instantiate a Supervisor node """

    options = ["FINISH"] + members
    systemPrompts = (
        "You are a supervisor tasked with managing a conversation between the" 
        f" following workers: {members}. Given the following request," 
        " First, delegate to researchTeam to gather background knowledge."
        " Then, delegate to dataScienceTeam to retrieve the dataset, preprocess it, train and evaluate a model."
        " Then, delegate to writingTeam to produce a report."
        " Review the writing team's output and ask the user for feedback. If feedback is given, pass it back to researchTeam."
        " When finished, respond with FINISH."
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
            goto = END

        # Handoff control to another agent
        return Command(
            goto=goto, 
            update={"next":goto}
        )
    
    return supervisor 


