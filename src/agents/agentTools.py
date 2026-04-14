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

# Scikit Learn
import pandas as pd
from pandas import DataFrame
from sklearn.ensemble import RandomForestRegressor

# RDKit
from rdkit import Chem
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator

# TDC Dataset
from sklearn.metrics import r2_score
from tdc.single_pred import ADME

@tool
def scrapeWebpages(urls: List[str]) -> str:

    """ User requests and bs4 to scrape the proivided the web page for detailed information"""
    
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

    results = []

    for url in urls:
        
        try:

            # Use WebBaseLoader to scrape the webpage and retrieve its content as documents
            loader = WebBaseLoader(urls)
            docs = loader.load()

            # Append the content of each document to the results list, wrapped in <Document> tags with the title as metadata
            for doc in docs:
                results.append(
                    f'<Document name="{doc.metadata.get("title","")}">\n{doc.page_content}\n</Document>'
                )

        except Exception as e:

            # If there is an error during scraping, append an error message to the results list, wrapped in <Error> tags with the URL as metadata
            results.append(f'<Error url="{url}">Failed to scrape: {str(e)}</Error>')


    # Run a list comprehension that parses each doc in the doc lists retrieved
    return "\n\n".join(
        results
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

    with open(fileToUse, "w", encoding="utf-8") as file:
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

    with open(fileToUse, "r", encoding="utf-8") as file:
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
    
    with open(fileToUse, "w", encoding="utf-8") as file:
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

    with open(fileToUse, "r", encoding="utf-8") as file:
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
    with open(fileToUse, "w", encoding="utf-8") as file:
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




# In-memory global var to flexibly pass Dataframe JSON between tools (agents cannot parse dataframes)
jsonDataset = {}
model = None

@tool
def obtainAdmeDataset(
    datasetName: Annotated[str, "The name of requested dataset to obtain from TDC python library"]
):
    
    """Extract the dataset name from prompt, obtain it from TDC python library and 
    return the JSON dataset """

    data = ADME(name = datasetName)
    
    # The entire dataset (in pandas dataframe) 
    df = data.get_data()

    # The train, val, test split
    splits = data.get_split()

    # Convert dataset to JSON for other agent tools
    jsonDataset["train"] = splits["train"].to_json(orient="records")
    jsonDataset["valid"] = splits["valid"].to_json(orient="records")
    jsonDataset["test"] = splits["test"].to_json(orient="records")

    return "ADME obtained and converted into JSON for further processing"


@tool
def featurizeRawSmile(

    ### LangChain cannot read DataFrame - find a way to convert this
    # dataset: Annotated[dict, "The dataset that contains a raw SMILE column"]
):
    
    """Convert columns with raw SMILES into fingerprints and return featurised dataset."""

    # Convert in-memory JSON back into pandas Dataframe
    df = pd.read_json(jsonDataset["train"], orient="records")
    
    if(df is None):
        return "Dataframe is empty. It could be that we might have use this tool before obtaining an ADME Dataset."

    # An function to convert raw smiles into fingerprint
    def smilesToFingerprint(
        smiles: Annotated[str, "The SMILES string to be converted into fingerprints"]        
    ):
        
        mol = Chem.MolFromSmiles(smiles)
        
        # [Guard clause]
        if mol is None:
            return [0] * 2048
        
        generator = GetMorganGenerator(radius = 3, fpSize = 2048)
        fingerprint = list(generator.GetFingerprintAsNumpy(mol))

        return fingerprint
    
    
    featurisedDataset = df["Drug"].apply(smilesToFingerprint)

    # Convert back to JSON and update jsonDataset
    jsonDataset = featurisedDataset.to_json()

    return "Dataset featurized. JSON Dataframe updated."


@tool
def fitRandomForestRegressor(
    # trainingDataset: Annotated[DataFrame, "The TDC training dataset to be used for model fitting"],
):
    
    """Train random forest with training dataset and return the model"""
    
    # Read in-memory jsonDataset and extract training features and target
    xTrain = pd.read_json(jsonDataset["train"]["Drug"], orient="records")
    yTrain = pd.read_json(jsonDataset["train"]['Y'], orient="records")

    model = RandomForestRegressor(
        random_state = 42
    )

    model.fit(xTrain, yTrain)

    return "Model fitted and ready to test."

@tool
def evaluateModel(
    # model: Annotated[RandomForestRegressor, "The trained model to be evaluated"],
    # testDataset: Annotated[str, "The test dataset to evaluate the model against"]
):
    
    """Evaluate r2 score of model on test dataset and return the score"""
    
    # xTrain = pd.read_json(jsonDataset["train"]["Drug"], orient="records")
    # yTrain = pd.read_json(jsonDataset["train"]['Y'], orient="records")
    
    xTest = pd.read_json(jsonDataset["test"]["Drug"], orient="records")
    
    # Target
    yTest = pd.read_json(jsonDataset["test"]["Y"], orient="records")
    
    # Predict
    yPred = model.predict(xTest)

    score = r2_score(yTest, yPred)

    return f"Model evaluated. R2 Score: {score:.4f}%"