from tools.search import search


TOOLS = {
    "search": search
}


def run_tool(name, argument):

    tool = TOOLS.get(name)

    if not tool:
        return "Tool not found."

    return tool(argument)