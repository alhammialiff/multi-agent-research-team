
import os

def readSpecFile(fileName: str) -> str:
    
    """ Return Text From Prompt Specification File"""

    fileToUse = os.path.join(os.getcwd(), "src", "specs", fileName)
    start = 0
    end = None

    with open(fileToUse, "r") as file:
        lines = file.readlines()

    if start is None:
        start = 0

    return "\n".join(lines[start:end])

