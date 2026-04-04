from json import tool

from dotenv import load_dotenv
import os
from typing import Annotated, Dict, List, Optional

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.tools import tool 

@tool
def scrapeWebpages(urls: List[str]) -> str:

    """ User requests and bs4 to scrape the proivided the web page for detailed information"""
    
    loader = WebBaseLoader(urls)
    docs = loader.load()

    return "\n\n".join(
        [
            f'<Document name="{doc.metadata.get("title","")}">\n{doc.page_content}\n</Document>'
        ]
    )


@tool
def createOutline(
    points: Annotated[List[str], "List of main points or sections"],
    fileName: Annotated[str, "File path to save the outline"]
) -> Annotated[str, "Path of the saved outline file"]:
    
    """ Create and save an outline"""

    fileToUse = os.path.join(os.getcwd(), "temp", fileName)

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
    fileName: Annotated[str, "File path to save the document"]
):
    
    """Create and save a text document"""

    fileToUse = os.path.join(os.getcwd(), "temp", fileName)
    
    with open(fileToUse, "w") as file:
        file.write(content)

    return f"Document saved to {fileName}"
    

@tool
def editDocument(
    fileName: Annotated[str, "File path to save the document"],
    insert: Annotated[Dict[int, str], "Dictionary where key is the line number and value is the text to be inserted at the line number"]
):
    
    """Edit a document by inserting text at specified line numbers"""
    
    fileToUse = os.path.join(os.getcwd(), "temp", fileName)

    with open(fileToUse, "w") as file:
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
    with open(fileName, "w") as file:
        file.writelines(lines)

    return f"Document edited and saved to {fileName}"



def main():

    print()


if __name__ == "__main__":

    main()