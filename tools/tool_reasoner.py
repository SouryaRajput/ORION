from Core.ai import ai_think_and_reply
from tools.registry import run_tool


MAX_TOOL_STEPS = 5


def run_tool_reasoning(user_input):

    tool_result = None

    for _ in range(MAX_TOOL_STEPS):

        result = ai_think_and_reply(user_input, tool_result=tool_result)

        intent = result.get("intent")
        reply = result.get("reply")
        tool = result.get("tool")
        tool_input = result.get("input")

        if intent != "tool":
            return reply

        if not tool:
            return "Tool request missing."

        tool_result = run_tool(tool, tool_input)

    return "I couldn't complete the task after several attempts."