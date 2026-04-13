
from agents.supervisor import State

def optimiseContext(state: State, lastN: int = 4) -> dict:

    """Keep original task + last N messages to preserve intent without bloating context """
    
    original = state["messages"][:1]
    recent = state["messages"][-(lastN):]

    # Return first and last N message (trim while preserving context)
    return {**state, "messages": original + recent}