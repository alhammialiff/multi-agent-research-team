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
from langgraph import graph
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.types import Command, Send
from langgraph.prebuilt import create_react_agent

from agents.researchTeam import searchNode, webScrapperNode, researchSupervisorNode
from agents.writingTeam import chartGeneratingNode, docWritingNode, docWritingSupervisorNode, noteTakingNode
from agents.supervisor import State, makeSupervisorNode
from agents.divisionLead import State, makeDivisionLead
from utils.printGraphToPng import printGraphToPng
from utils.readTextFile import readSpecFile

def main():

    # Sub-graph Research Team
    researchBuilder = StateGraph(State)
    researchBuilder.add_node("supervisor", researchSupervisorNode)
    researchBuilder.add_node("search", searchNode)
    researchBuilder.add_node("webScrapper", webScrapperNode)

    researchBuilder.add_edge(START, "supervisor")
    researchGraph = researchBuilder.compile()


    # Sub-graph Writing Team
    writingBuilder = StateGraph(State)
    writingBuilder.add_node("supervisor", docWritingSupervisorNode)
    writingBuilder.add_node("docWriter", docWritingNode)
    writingBuilder.add_node("noteTaker", noteTakingNode)
    writingBuilder.add_node("chartGenerator", chartGeneratingNode)

    writingBuilder.add_edge(START, "supervisor")
    writingGraph = writingBuilder.compile()

    # Main Graph: Division Leader
    divisionBuilder = StateGraph(State)

    # Define Division Lead and its graph relationship to the teams
    load_dotenv()
    llm = ChatOpenAI(model = "gpt-5-mini")

    divisionLead = makeDivisionLead(llm, ["researchTeam", "writingTeam"])

    divisionBuilder.add_node("divisionLead", divisionLead)
    divisionBuilder.add_node("researchTeam",researchGraph)
    divisionBuilder.add_node("writingTeam", writingGraph)

    divisionBuilder.add_edge(START, "divisionLead")
    divisionBuilder.add_edge("divisionLead","researchTeam")
    divisionBuilder.add_edge("researchTeam", "writingTeam")
    

    # Compile graph (the hierarchy)
    divisionGraph = divisionBuilder.compile()

    # Read spec file 
    SPEC_FILE_PATH = os.getenv("SPEC_FILE_PATH")

    promptFromSpecFile = readSpecFile(SPEC_FILE_PATH)
    
    for s in divisionGraph.stream(
        {
            "messages": [
                HumanMessage(
                    # content="Write a report on how an AI-enabled Drug Discovery pipeline can be developed. Give examples of how Machine Learning, Deep Learning or Foundational Models can be used to advance this efforts. Introduce sections like Introduction, the Sections body, and Conclusion. Save report in markdown file.")
                    content=promptFromSpecFile
                )
            ]
        },
        {
            "recursion_limit": 30
        }
    ):
        print(s)
        print("----")


    # printGraphToPng(divisionGraph)



if __name__ == "__main__":

    main()