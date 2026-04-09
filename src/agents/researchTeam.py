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

from agents.agentTools import scrapeWebpages
from agents.supervisor import State, makeSupervisorNode

load_dotenv()
llm = ChatOpenAI(model = "gpt-5-mini")
tavilyTool = TavilySearch(max_result=3)

searchAgent = create_react_agent(llm, tools=[tavilyTool])


def searchNode(state: State) -> Command[Literal["supervisor"]]:

    result = searchAgent.invoke(state)

    return Command(
        update = {
            "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name="search")]
        },
        goto = "supervisor"
    )

webScrapperAgent = create_react_agent(llm, tools=[scrapeWebpages])


def webScrapperNode(state: State) -> Command[Literal["supervisor"]]:

    result = webScrapperAgent.invoke(state)

    return Command(
        update = {
            "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name="webScrapper")]
        },
        goto = "supervisor"
    )



researchSupervisorNode = makeSupervisorNode(llm, ["search", "webScrapper"])
