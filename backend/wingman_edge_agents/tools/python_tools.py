"""Tools for executing Python code using LangChain Experimental's PythonREPLTool."""
from langchain_experimental.tools import PythonREPLTool
from langchain.tools import tool

from .data_models import RunPythonCodeArgs

# Instantiate the PythonREPLTool
_python_tool = PythonREPLTool()

@tool(
    parse_docstring=True, 
    args_schema=RunPythonCodeArgs,
    description="""Executes Python code in an isolated REPL environment and returns the output (stdout).
    This tool is ideal for performing complex calculations, data processing, 
    running simulations, or utilizing specific Python libraries.
    
    Examples:
    - Math operations: "import math\\nprint(math.pow(2, 10))"
    - List processing: "data = [1, 2, 3, 4]\\nprint([x*x for x in data])"
    
    When to use: Use for complex logic, math, or data transformations. Always use print() to see results. 
    The REPL maintains state within a single execution."""
)
def run_python_code(query: str) -> str:
    """Executes Python code in an isolated REPL environment."""
    args = RunPythonCodeArgs(query=query)
    try:
        # PythonREPLTool usually takes 'query' (the code) as valid input
        return _python_tool.run(args.query)
    except Exception as e:
        return f"Error executing Python code: {str(e)}"

__all__ = ["run_python_code"]
