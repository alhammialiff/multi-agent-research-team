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
from langgraph.types import Command, Send, interrupt
from langgraph.prebuilt import create_react_agent


class State(MessagesState):
    
    # The next node that it is going to hand over to
    next: str


def makeDivisionLead(llm: BaseChatModel, members: List[str]) -> str:

    """ A function to instantiate a Division Lead node """
    options = ["FINISH"] + members
    systemPrompts = (
        f"You are the division lead for two teams: {members}"
        " If research has not been done yet, delegate to the research team."
        " If the writing team has not produced a first draft yet, delegate to the writing team. Always review the output of each team before passing"
        " If the writing team has produced a draft, review it first, and ask user for feedback. If user has feedback, pass it back to the research team for further research."
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

        # [Guarded Clause] If there is a report from the writing team, interrupt the flow to ask user for feedback on the report before deciding where to handoff control
        if hasReportFromWritingTeam(state):

            # Interrupt the flow to ask user for feedback on the report from the writing team
            answer = interrupt("Division Lead: Do you find the report satisfactory? (y/n) ")
            

            if answer.lower() == "yes" or answer.lower() == "y" or answer.upper() == "Y":

                # End process if user is satisfied with the report
                return Command(
                    goto=END,
                    update={
                        "messages": state["messages"] + [
                            HumanMessage(content=f"Division lead has no further feedback, ending the process", name="divisionLead")             
                        ]
                    }
                )
            
            else:

                # Handoff control to research back
                return Command(
                    goto="researchTeam",
                    update={
                        "messages": state["messages"] + [
                            HumanMessage(content=f"Division lead has feedback on the report, asking research team to do further research", name="divisionLead")             
                        ]
                    }
                )

        # Handoff control to another agent
        return Command(
            goto=goto,
            update={
                "messages": state["messages"] + [
                    HumanMessage(content=f"Division lead selected {goto}", name="divisionLead")             
                ]
            }
        )
    
    def hasReportFromWritingTeam(state: State) -> bool:

        for message in state["messages"]:
            if message.name == "docWriter":
                return True
        
        return False
    
    return divisionLead