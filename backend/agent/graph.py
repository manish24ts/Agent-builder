from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from backend.tools.tools import get_tools_by_names

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


def build_agent_graph(system_prompt: str, tool_names: List[str], model: str = "llama-3.3-70b-versatile", temperature: float = 0.7):
    """
    Construct a compiled LangGraph agent for one Agent config.

    Raises RuntimeError (not a raw exception) if the model can't be initialized,
    so the caller (chat route) can return a clean error instead of a 500 crash.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in backend/.env.")

    tools = get_tools_by_names(tool_names)  # silently skips any tool that fails to load

    llm = ChatGroq(model=model, temperature=temperature, api_key=GROQ_API_KEY, streaming=True)
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    def call_model(state: MessagesState) -> dict:
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt), *messages]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)

    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
    else:
        graph.set_entry_point("agent")
        graph.add_edge("agent", END)

    return graph.compile()