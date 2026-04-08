import os
import traceback

from langgraph.graph.state import CompiledStateGraph

def printGraphToPng(graphToPrint: CompiledStateGraph):

    try:

        pathToFile = os.path.join(os.getcwd(), "graph-structure", "hierarchy.png")
        pathToDir = os.path.join(os.getcwd(), "graph-structure")

        os.makedirs(pathToDir, exist_ok=True)

        with open(pathToFile, "wb") as file:
            
            file.write(
                graphToPrint.get_graph().draw_mermaid_png()
            )
        
    except Exception as e:

        print(e)
        traceback.print_stack()