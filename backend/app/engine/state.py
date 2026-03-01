"""AgentState definition for the LangGraph ReAct agent loop."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State that flows through the LangGraph ReAct agent.

    - messages: Conversation history between the LLM and tools.
      Uses LangGraph's add_messages reducer to append new messages.
    - run_id: UUID string of the current AgentRun, used for logging.
    - platform_configs: Decrypted platform info available to tool functions.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    run_id: str
    platform_configs: list[dict]
