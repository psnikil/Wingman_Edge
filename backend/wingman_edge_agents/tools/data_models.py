from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from typing import Union, List, Optional, Literal
from pydantic import BaseModel, Field

# --- CLI Tools ---
class ExecuteCommandArgs(BaseModel):
    commands: Union[str, List[str]] = Field(
        ..., 
        description="The shell command or list of commands to execute. Examples: 'ls -la', ['mkdir test', 'cd test', 'touch file.txt']. Use strings for single commands and lists for sequential operations."
    )

# --- File Tools ---
class CreateFileArgs(BaseModel):
    file_path: str = Field(..., description="The absolute or relative path where the file should be created. Example: './data/config.json'")

class DeleteFileArgs(BaseModel):
    file_path: str = Field(..., description="The path of the file to delete. Example: 'temp_log.txt'")

class WriteFileArgs(BaseModel):
    file_path: str = Field(..., description="The path to the existing file to be modified.")
    content: str = Field(..., description="The content to write or append to the file.")
    mode: Literal["write", "append"] = Field(
        "write", 
        description="'write' to overwrite the entire file, 'append' to add the content to the end of the file. Defaults to 'write'."
    )

class RenameFileArgs(BaseModel):
    old_path: str = Field(..., description="The current path of the file or directory.")
    new_path: str = Field(..., description="The new path or filename. Can be used to move files as well.")

class ListFilesArgs(BaseModel):
    directory_path: str = Field("./", description="The directory path to list contents of. Defaults to the current workspace root './'.")

class ReadFileArgs(BaseModel):
    file_path: str = Field(..., description="The path of the file to read.")

class CopyFileArgs(BaseModel):
    source_path: str = Field(..., description="The path of the file to copy.")
    destination_path: str = Field(..., description="The destination path where the copy will be created.")

class FileSearchArgs(BaseModel):
    query: str = Field(..., description="The search term or regex pattern to search for filenames. Example: '.*\\.py' for python files.")
    directory_path: str = Field(".", description="The directory to start the search from. Defaults to '.' (current directory).")

# --- OS Tools ---
class OpenBrowserArgs(BaseModel):
    url: str = Field(..., description="The full URL to open in the default web browser. Example: 'https://github.com'")

class OpenAppArgs(BaseModel):
    app_name: str = Field(..., description="The command name of the application to launch. Example: 'gedit' on Linux or 'notepad' on Windows.")

class TakeScreenshotArgs(BaseModel):
    filename: str = Field("screenshot.png", description="The filename for the saved screenshot. Defaults to 'screenshot.png'.")

class SearchOSFilesArgs(BaseModel):
    pattern: str = Field(..., description="The filename pattern to search for. Supports wildcards like '*.pdf'.")
    search_path: str = Field(".", description="The root directory for the search. Defaults to current directory.")

class DownloadFileArgs(BaseModel):
    url: str = Field(..., description="The URL of the file to download.")
    save_path: str = Field(..., description="The local path where the file should be saved.")

# --- Python Tools ---
class RunPythonCodeArgs(BaseModel):
    query: str = Field(
        ..., 
        description="The Python code string to execute in the REPL. Include imports if necessary. Example: \"import math\\nprint(math.sqrt(16))\""
    )

# --- Web Tools ---
class WebSearchArgs(BaseModel):
    query: str = Field(..., description="The search query or topic to look up.")
    context: Optional[str] = Field(None, description="Additional context or background information to help optimize the search query for better results.")

class DDGSearchArgs(DuckDuckGoSearchAPIWrapper):
    query: str = Field(..., description="The search query or topic to look up.")
    # context: Optional[str] = Field(None, description="Additional context or background information to help optimize the search query for better results.")
# --- Think Tools ---
class ThinkArgs(BaseModel):
    reflection: str = Field(..., description="Your detailed reflection on research progress, findings, gaps, and next steps.")