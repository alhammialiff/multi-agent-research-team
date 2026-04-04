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

from agents.researchTeam import searchNode, webScrapperNode, researchSupervisorNode
from agents.writingTeam import chartGeneratingNode, docWritingNode, docWritingSupervisorNode, noteTakingNode
from agents.supervisor import State, makeSupervisorNode

def main():

    researchBuilder = StateGraph(State)
    researchBuilder.add_node("supervisor", researchSupervisorNode)
    researchBuilder.add_node("search", searchNode)
    researchBuilder.add_node("webScrapper", webScrapperNode)

    researchBuilder.add_edge(START, "supervisor")

    researchGraph = researchBuilder.compile()

    writingBuilder = StateGraph(State)
    writingBuilder.add_node("supervisor", docWritingSupervisorNode)
    writingBuilder.add_node("docWriter", docWritingNode)
    writingBuilder.add_node("noteTaker", noteTakingNode)
    writingBuilder.add_node("chartGenerator", chartGeneratingNode)

    writingBuilder.add_edge(START, "supervisor")
    writingGraph = writingBuilder.compile()

    for s in writingGraph.stream(
        {
            "messages": [HumanMessage(content="Write an outline for a poem about dogs and after that write the poem itself and store it")]
        },
        {
            "recursion_limit": 30
        }
    ):
        print(s)
        print("----")



if __name__ == "__main__":

    main()