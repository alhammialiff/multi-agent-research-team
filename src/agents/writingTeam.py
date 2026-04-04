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

from agents.supervisor import State, makeSupervisorNode
from agents.agentTools import createOutline, editDocument, readDocument, writeDocument, pythonReplTool, scrapeWebpages


llm = ChatOpenAI(model = "gpt-4o")

docWriterAgent = create_react_agent(
    llm,
    tools = [writeDocument,editDocument,readDocument],
    prompt= (
        "You can read, write and edit documents based on note taker's outlines. \
            Don't ask follow up questions"
    )
)

def docWritingNode(state: State) -> Command[Literal["supervisor"]]:

    result = docWriterAgent.invoke(state)

    return Command(
        update = {
            "messages": [
                HumanMessage(content= result["messages"][-1].content, name = "docWriter")
            ]
        },
        goto = "supervisor"
    )


noteTakingAgent = create_react_agent(
    llm,
    tools = [createOutline,readDocument],
    prompt=(
        "You can read documents and create outlines for the document writers. \
            Don't ask follow up questions."
    )
)

def noteTakingNode(state: State) -> Command[Literal["supervisor"]]:
    
    result = noteTakingAgent.invoke(state)

    return Command(
        update = {
            "messages": [
                HumanMessage(content = result["messages"][-1].content, name = "docWriter")
            ]
        },
        goto = "supervisor"
    )

chartGeneratingAgent = create_react_agent(
    llm,
    tools = [readDocument,pythonReplTool]
)

def chartGeneratingNode(state: State) -> Command[Literal["supervisor"]]:
    
    result = chartGeneratingAgent.invoke(state)

    return Command(
        update = {
            "messages": [
                HumanMessage(content = result["messages"][-1].content, name = "chartGenerator")
            ]
        },
        goto = "supervisor"
    )


docWritingSupervisorNode = makeSupervisorNode(
    llm,
    ["docWriter", "noteTaker", "chartGenerator"]
)