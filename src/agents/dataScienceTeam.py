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

from agents.agentTools import evaluateModel, featurizeRawSmile, fitRandomForestRegressor, obtainAdmeDataset
from agents.supervisor import State, makeSupervisorNode
from utils.optimiseContext import optimiseContext


load_dotenv()
llm = ChatOpenAI(model = "gpt-5-mini")
tavilyTool = TavilySearch(max_result=3)



# Instantiate Agents - Dataset Search Agent
datasetSearchAgent = create_react_agent(llm, tools=[obtainAdmeDataset])

def searchDatasetNode(state: State) -> Command[Literal["supervisor"]]:

    result = datasetSearchAgent.invoke(optimiseContext(state))

    return Command(
        goto="preprocessDataset",
        update = {
            "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name="searchDataset")]
        }
    )


# Instantiate Agents - Data Preprocessing Agent
dataPreprocessingAgent = create_react_agent(llm, tools=[featurizeRawSmile])

def preprocessDatasetNode(state: State) -> Command[Literal["supervisor"]]:

    trimmedState = {**state, "messages": state["messages"][-6:]}

    result = dataPreprocessingAgent.invoke(optimiseContext(state))
    
    # [DEBUG] Length of context at this point 
    total_chars = sum(len(str(m.content)) for m in state["messages"])
    print(f"[DEBUG] preprocessDataset — {len(state['messages'])} messages, ~{total_chars} chars")
    
    return Command(
        goto="trainModel",
        update = {
            "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name="preprocessDataset")]
        }
    )


# Instantiate Agents - Model Training Agent
modelTrainingAgent = create_react_agent(llm, tools=[fitRandomForestRegressor])

def trainModelNode(state: State) -> Command[Literal["supervisor"]]:

    result = modelTrainingAgent.invoke(optimiseContext(state))

    return Command(
        goto="evaluateModel",
        update = {
            "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name="trainModel")]
        }
    )

# Instantiate Agents - Model Evaluation Agent
modelEvaluationAgent = create_react_agent(llm, tools=[evaluateModel])

def evaluateModelNode(state: State) -> Command[Literal["supervisor"]]:

    result = modelEvaluationAgent.invoke(optimiseContext(state))

    return Command(
        goto="supervisor",
        update={
            "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name="evaluateModel")]
        }
    )

dataScienceSupervisor = makeSupervisorNode(llm, ["searchDataset", "preprocessDataset", "trainModel", "evaluateModel"])