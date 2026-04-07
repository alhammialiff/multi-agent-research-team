from typing import Literal, TypedDict

import certifi

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

@tool
def scrapeWebpages(urls: List[str]) -> str:

    """ User requests and bs4 to scrape the proivided the web page for detailed information"""
    
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

    loader = WebBaseLoader(urls)
    docs = loader.load()

    # return "\n\n".join(
    #     [
    #         f'<Document name="{docs.metadata.get("title","")}">\n{docs.page_content}\n</Document>'
    #     ]
    # )

    # Run a list comprehension that parses each doc in the doc lists retrieved
    return "\n\n".join(
        f'<Document name="{doc.metadata.get("title","")}">\n{doc.page_content}\n</Document>'
        for doc in docs
    )


@tool
def createOutline(
    points: Annotated[List[str], "List of main points or sections"],
    fileName: Annotated[str, "File path to save the outline"]
) -> Annotated[str, "Path of the saved outline file"]:
    
    """ Create and save an outline"""

    tempDir = os.path.join(os.getcwd(), "temp")
    os.makedirs(tempDir, exist_ok=True)
    fileToUse = os.path.join(tempDir, fileName)

    with open(fileToUse, "w") as file:
        for i, point in enumerate(points):
            file.write(f"{i+1}. {point}\n")

    return f"Outline saved to  {fileName}"


@tool
def readDocument(
    fileName: Annotated[str, "File path to read the document from"],
    start: Annotated[Optional[int], "The start line. Default is 0"] = None,
    end: Annotated[Optional[int], "The end line. Default is None"] = None
):

    """ Read the specified document"""

    fileToUse = os.path.join(os.getcwd(), "temp", fileName)

    with open(fileToUse, "r") as file:
        lines = file.readlines()

    if start is None:
        start = 0

    return "\n".join(lines[start:end])


@tool
def writeDocument(
    content: Annotated[str, "Test content to be returned to the documnet"],
    fileName: Annotated[str, "File path to save the document."]
):
    
    """Create and save a text document"""

    tempDir = os.path.join(os.getcwd(), "temp")
    os.makedirs(tempDir, exist_ok=True)
    fileToUse = os.path.join(tempDir, fileName)
    
    with open(fileToUse, "w") as file:
        file.write(content)

    return f"Document saved to {fileName}"
    

@tool
def editDocument(
    fileName: Annotated[str, "File path to save the document"],
    insert: Annotated[Dict[int, str], "Dictionary where key is the line number and value is the text to be inserted at the line number"]
):
    
    """Edit a document by inserting text at specified line numbers"""
    
    tempDir = os.path.join(os.getcwd(), "temp")
    os.makedirs(tempDir, exist_ok=True)
    fileToUse = os.path.join(tempDir, fileName)

    with open(fileToUse, "r") as file:
        lines = file.readlines()

    sortedInserts = sorted(insert.items())

    # Edit line based on lineNumber given 
    for lineNumber, text in sortedInserts:

        # Lines are only edittable where there are existing ones
        if 1 <= lineNumber <= len(lines) + 1:
            lines.insert(lineNumber-1, text + "\n")
        else:
            return f"Error: line number {lineNumber} is out of range"
        
    # Save file
    with open(fileToUse, "w") as file:
        file.writelines(lines)

    return f"Document edited and saved to {fileName}"


@tool
def pythonReplTool(
    code: Annotated[str, "The python code to execute to generate your chart"],
):
    """Use this to execute python code, If you want to see the output of any value,
    you should print it with `print(...)`. This is visible to the user"""

    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    return f"Successfully executed: \n ```python \n{code}``` \n Stdout: {result}"