""" These are tools to steer the LLM eg: think_tool- this forces the LLM to reason about its response"""

from langchain.tools import tool
from backend.wingman_edge_agents.tools.data_models import ThinkArgs

@tool(
    parse_docstring=True, 
    args_schema=ThinkArgs,
    description="""Tool for strategic reflection on task progress and decision-making.

    Use this tool ONLY after gathering information for the given task and use the tool to analyze results and plan next steps systematically.
    This creates a deliberate pause in the task workflow for quality decision-making.

    When to use:
    - After information about the task has been gathered: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing gaps/issues in the gathered information: What specific information am I still missing/ what are the issues or errors I am facing?
    - Before concluding task tool use: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing/ issue or errors are present?
    3. Quality evaluation - Do I have sufficient information for a good answer?
    4. Strategic decision - what should I do next? (use another tool or provide my answer?)

    Don Nots
    1. Do not return the tool call in the reflection
    
    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    
)
def think_tool(reflection: str) -> str:
    reflection = str(reflection).strip()
    return f"Reflection recorded: {reflection}"