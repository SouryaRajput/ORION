from Core.ai import ai_think_and_reply
from tools.registry import run_tool


MAX_RESEARCH_STEPS = 6


def run_research(user_input):

    tool_result = None
    collected_results = []

    for _ in range(MAX_RESEARCH_STEPS):

        result = ai_think_and_reply(user_input, tool_result=tool_result)

        intent = result.get("intent")
        reply = result.get("reply")
        tool = result.get("tool")
        tool_input = result.get("input")

        if intent != "tool":
            return reply

        if not tool:
            return "I couldn't determine which tool to use."

        tool_result = run_tool(tool, tool_input)

        collected_results.append(tool_result)

    return "I couldn't complete the research task."