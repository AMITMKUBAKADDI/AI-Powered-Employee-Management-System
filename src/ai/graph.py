# src/ai/graph.py
"""LangGraph workflow for orchestrating conversation state, tool invocation, and bounded loops."""

import json
from typing import Annotated, Sequence, TypedDict, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from src.ai.prompts import SYSTEM_PROMPT
from src.ai.tools import ALL_TOOLS, READ_ONLY_TOOLS
from src.ai.llm import get_llm


class ChatbotState(TypedDict):
    """Conversation state representation with add_messages reducer."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_role: str
    iteration_count: int
    pending_confirmation: Optional[Dict[str, Any]]


def create_agent_graph():
    """Build and compile the LangGraph conversation graph."""
    llm = get_llm()
    if llm is None:
        return None

    # Map tools by name for manual invocation in the tool node
    tools_by_name = {tool.name: tool for tool in ALL_TOOLS}

    def assistant_node(state: ChatbotState) -> Dict[str, Any]:
        """Node for LLM invocation with role-specific tool binding."""
        role = state.get("user_role", "user").lower()
        active_tools = ALL_TOOLS if role == "admin" else READ_ONLY_TOOLS
        llm_with_tools = llm.bind_tools(active_tools)

        # Ensure system prompt is present at the start of context
        messages = list(state["messages"])
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(
                content=f"{SYSTEM_PROMPT}\n\nCurrent User Role: {role.upper()}\n"
            )
            messages = [system_msg] + messages

        response = llm_with_tools.invoke(messages)
        current_iter = state.get("iteration_count", 0) + 1

        return {
            "messages": [response],
            "iteration_count": current_iter
        }

    def tools_node(state: ChatbotState) -> Dict[str, Any]:
        """Node that executes tools called by the LLM and formats results."""
        last_message = state["messages"][-1]
        tool_messages = []
        pending_conf = None
        user_role = state.get("user_role", "user")

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            for tc in last_message.tool_calls:
                tool_name = tc["name"]
                tool_args = dict(tc["args"])

                # Inject user_role if the tool schema accepts it
                if "user_role" in tool_args or tool_name in ["create_employee", "update_employee", "deactivate_employee"]:
                    tool_args["user_role"] = user_role

                if tool_name in tools_by_name:
                    tool_fn = tools_by_name[tool_name]
                    try:
                        result = tool_fn.invoke(tool_args)
                    except Exception as err:
                        result = json.dumps({"status": "error", "message": f"Execution error: {str(err)}"})

                    # Check if tool response requests user confirmation
                    try:
                        parsed = json.loads(result) if isinstance(result, str) else result
                        if isinstance(parsed, dict) and parsed.get("status") == "confirmation_required":
                            pending_conf = parsed
                    except Exception:
                        pass

                    tool_messages.append(
                        ToolMessage(
                            content=str(result),
                            tool_call_id=tc["id"],
                            name=tool_name
                        )
                    )
                else:
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error: Unknown tool '{tool_name}'",
                            tool_call_id=tc["id"],
                            name=tool_name
                        )
                    )

        return {
            "messages": tool_messages,
            "pending_confirmation": pending_conf
        }

    def should_continue(state: ChatbotState) -> str:
        """Evaluate whether to run tools or terminate conversation loop."""
        last_message = state["messages"][-1]
        iteration = state.get("iteration_count", 0)

        # Bounded loop limit (prevent infinite tool calling)
        if iteration >= 5:
            return END

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"

        return END

    workflow = StateGraph(ChatbotState)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", tools_node)

    workflow.set_entry_point("assistant")
    workflow.add_conditional_edges("assistant", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "assistant")

    return workflow.compile()


def extract_text_content(content: Any) -> str:
    """Safely extract plain text from Gemini AIMessage content (which can be str or list of dicts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content) if content is not None else ""


def run_chatbot_workflow(
    user_prompt: str,
    history: List[BaseMessage],
    user_role: str = "user"
) -> Dict[str, Any]:
    """Execute the conversation workflow and return the final answer and messages."""
    app = create_agent_graph()
    if app is None:
        return {
            "answer": "⚠️ Google Gemini API Key is missing or invalid. Please configure `GEMINI_API_KEY` in your `.env` file to chat with the AI assistant.",
            "history": history,
            "pending_confirmation": None,
            "tool_calls_executed": []
        }

    messages = list(history) + [HumanMessage(content=user_prompt)]
    initial_state: ChatbotState = {
        "messages": messages,
        "user_role": user_role,
        "iteration_count": 0,
        "pending_confirmation": None
    }

    try:
        final_state = app.invoke(initial_state)
        final_messages = list(final_state["messages"])
        last_msg = final_messages[-1]
        answer = extract_text_content(last_msg.content) if isinstance(last_msg, AIMessage) else str(last_msg)

        # Track any executed tool calls for UI transparency
        tool_calls_executed = []
        for m in final_messages:
            if isinstance(m, AIMessage) and m.tool_calls:
                for tc in m.tool_calls:
                    tool_calls_executed.append(tc)

        return {
            "answer": answer,
            "history": final_messages,
            "pending_confirmation": final_state.get("pending_confirmation"),
            "tool_calls_executed": tool_calls_executed
        }
    except Exception as exc:
        return {
            "answer": f"An error occurred while generating the response: {str(exc)}",
            "history": messages,
            "pending_confirmation": None,
            "tool_calls_executed": []
        }
