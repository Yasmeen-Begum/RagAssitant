# LangGraph Guide

LangGraph is a library for building stateful, multi-actor applications with LLMs, built on top of LangChain. It allows you to define circular flows, loops, and conditional routing logic, making it ideal for agentic systems.

## Key Concepts

* **State**: LangGraph represents applications as graphs where each node receives a shared state and returns updates to that state. The state is represented as a typed dictionary or a Pydantic model.
* **Nodes**: Nodes are standard Python functions or runnable components that perform actions (e.g. LLM calls, tools, database queries) and return updates to modify the graph's State.
* **Edges**: Edges define how control flows from one node to another.
  * *Normal Edges*: Direct connections, e.g. from Node A to Node B.
  * *Conditional Edges*: Dynamic routing based on a function that evaluates the state and decides the next node.

## Defining a Simple Graph

Here is an example of creating a simple workflow with LangGraph:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

# 1. Define the State schema
class AgentState(TypedDict):
    query: str
    messages: list
    attempts: int

# 2. Define the Nodes
def analyze_node(state: AgentState):
    print("Analyzing query...")
    return {"messages": ["Query analyzed."]}

def execute_node(state: AgentState):
    print("Executing action...")
    return {"messages": ["Action executed."]}

# 3. Define the Router (for conditional edge)
def should_continue(state: AgentState):
    if state.get("attempts", 0) < 3:
        return "execute"
    return "end"

# 4. Build the Graph
workflow = StateGraph(AgentState)

workflow.add_node("analyze", analyze_node)
workflow.add_node("execute", execute_node)

workflow.set_entry_point("analyze")

# Add normal edge
workflow.add_edge("execute", "analyze")

# Add conditional edge
workflow.add_conditional_edges(
    "analyze",
    should_continue,
    {
        "execute": "execute",
        "end": END
    }
)

# Compile graph
app = workflow.compile()
```

## State Reducers

By default, when a node returns a dictionary, LangGraph overwrites existing keys in the state. However, you can use *Reducers* to append or combine updates, which is extremely useful for maintaining list fields like a message list.

```python
from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class MessageState(TypedDict):
    # The add_messages reducer appends new messages to the list instead of overwriting it
    messages: Annotated[Sequence[BaseMessage], add_messages]
```
