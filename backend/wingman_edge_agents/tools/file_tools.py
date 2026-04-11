"""Tools for basic file system operations such as creating, deleting, and modifying files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from langchain.tools import tool

from backend.wingman_edge_agents.utils.root_fs import (
    format_dir_listing,
    read_text_limited,
    safe_resolve_under,
)
from .data_models import (
    CreateFileArgs, DeleteFileArgs, WriteFileArgs, 
    RenameFileArgs, ListFilesArgs, ReadFileArgs, 
    CopyFileArgs, FileSearchArgs
)

# Initialize tools
from langchain_community.tools.file_management.write import WriteFileTool
from langchain_community.tools.file_management.read import ReadFileTool
from langchain_community.tools.file_management.list_dir import ListDirectoryTool
from langchain_community.tools.file_management.delete import DeleteFileTool
from langchain_community.tools.file_management.move import MoveFileTool
from langchain_community.tools.file_management.copy import CopyFileTool
from langchain_community.tools.file_management.file_search import FileSearchTool

_write_tool = WriteFileTool()
_read_tool = ReadFileTool()
_list_tool = ListDirectoryTool()
_delete_tool = DeleteFileTool()
_move_tool = MoveFileTool()
_copy_tool = CopyFileTool()
_search_tool = FileSearchTool()

# Optional workspace root for ``read_workspace_file`` / ``list_workspace_directory``.
_WORKSPACE_ROOT: Path | None = None


def init_workspace_root(path: str | None) -> str:
    """Set (or clear) the root directory used by workspace-scoped file tools.

    Pass an absolute or user-expandable path to confine reads/lists under that directory.
    Pass ``None`` or an empty string to clear the root.

    Returns:
        A short status message.
    """
    global _WORKSPACE_ROOT
    if path is None or not str(path).strip():
        _WORKSPACE_ROOT = None
        return "Workspace root cleared."
    _WORKSPACE_ROOT = Path(path).expanduser().resolve()
    return f"Workspace root set to {_WORKSPACE_ROOT}"


@tool(
    parse_docstring=True, 
    args_schema=CreateFileArgs,
    description="""Creates a new file at the specified path with the provided content.
    Examples:
    - JSON config: create_file(file_path="settings.json")
    - Python script: create_file(file_path="hello.py")
    
    When to use: Use this to initialize new documents, configuration files, or source code."""
)
def create_file(file_path: str) -> str:
    """Creates a new file at the specified path."""
    args = CreateFileArgs(file_path=file_path)
    try:
        if os.path.exists(args.file_path):
            return f"File {args.file_path} already exists."
        with open(args.file_path, 'w', encoding='utf-8') as f:
            pass
        return f"File created successfully at {args.file_path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"


@tool(
    parse_docstring=True, 
    args_schema=DeleteFileArgs,
    description="""Permanently deletes a file at the specified path. CAUTION: Irreversible.
    Examples:
    - Removing a temp file: delete_file(file_path="temp_results.log")
    
    When to use: Use only when a file is no longer needed or was a temporary artifact."""
)
def delete_file(file_path: str) -> str:
    """Permanently deletes a file."""
    args = DeleteFileArgs(file_path=file_path)
    try:
        return _delete_tool.run({"file_path": args.file_path})
    except Exception as e:
        return f"Error deleting file: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=WriteFileArgs,
    description="""Modifies an existing file by overwriting ('write') or adding to the end ('append').
    write only a string, or markdown , no json objects
    Examples:
    - Overwrite: write_file(file_path="README.md", content="# New Title", mode="write")
    - Append: write_file(file_path="log.txt", content="New entry", mode="append")
    
    When to use: Use for quick updates or logging to existing files."""
)
def write_file(file_path: str, content: str, mode: Literal["write", "append"] = "write") -> str:
    """Modifies an existing file."""
    args = WriteFileArgs(file_path=file_path, content=content, mode=mode)
    try:
        append_flag = (args.mode == "append")
        return _write_tool.run({"file_path": args.file_path, "text": args.content, "append": append_flag})
    except Exception as e:
        return f"Error modifying file: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=RenameFileArgs,
    description="""Renames a file or directory, effectively moving it if the path changes.
    Examples:
    - Rename: rename_file(old_path="data.txt", new_path="data_v1.txt")
    - Move and Rename: rename_file(old_path="info.md", new_path="./docs/intro.md")
    
    When to use: Use to give files more descriptive names or to reorganize the project structure."""
)
def rename_file(old_path: str, new_path: str) -> str:
    """Renames a file or directory."""
    args = RenameFileArgs(old_path=old_path, new_path=new_path)
    try:
        return _move_tool.run({"source_path": args.old_path, "destination_path": args.new_path})
    except Exception as e:
        return f"Error renaming file: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=RenameFileArgs,
    description="""Moves a file or directory from one location to another.
    Example: move_file(old_path="data.txt", new_path="archive/data.txt")
    
    When to use: Use to reorganize files or move them into specific project directories."""
)
def move_file(old_path: str, new_path: str) -> str:
    """Moves a file or directory."""
    args = RenameFileArgs(old_path=old_path, new_path=new_path)
    try:
        return _move_tool.run({"source_path": args.old_path, "destination_path": args.new_path})
    except Exception as e:
        return f"Error moving file: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=ListFilesArgs,
    description="""Lists all files and subdirectories within a specified directory.
    Examples:
    - Root: list_files(directory_path="./")
    - Subdir: list_files(directory_path="services/")
    
    When to use: Primary tool for exploring the codebase and locating relevant files."""
)
def list_files(directory_path: str = "./") -> str:
    """Lists all files and subdirectories."""
    args = ListFilesArgs(directory_path=directory_path)
    try:
        return _list_tool.run({"dir_path": args.directory_path})
    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=ReadFileArgs,
    description="""Reads the full text content of a file.
    Examples:
    - Read script: read_file(file_path="main.py")
    - Read notes: read_file(file_path="notes.txt")
    
    When to use: Use to inspect source code, docs, or configs. Avoid for large binary files."""
)
def read_file(file_path: str) -> str:
    """Reads the full text content of a file."""
    args = ReadFileArgs(file_path=file_path)
    try:
        return _read_tool.run({"file_path": args.file_path})
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=CopyFileArgs,
    description="""Copies a file from source_path to destination_path.
    Example: copy_file(source_path="main.py", destination_path="main_backup.py")
    
    When to use: Use to create backups or duplicates of existing files."""
)
def copy_file(source_path: str, destination_path: str) -> str:
    """Copies a file from source_path to destination_path."""
    args = CopyFileArgs(source_path=source_path, destination_path=destination_path)
    try:
        return _copy_tool.run({"source_path": args.source_path, "destination_path": args.destination_path})
    except Exception as e:
        return f"Error copying file: {str(e)}"

@tool(
    parse_docstring=True, 
    args_schema=FileSearchArgs,
    description="""Searches for files matching a specific name pattern within a directory.
    Examples:
    - Finding tests: file_search(query="test_.*\\\\.py", directory_path="tests/")
    - Finding configs: file_search(query=".*config.*", directory_path=".")
    
    When to use: Use when you know part of a filename but not its exact location."""
)
def file_search(query: str, directory_path: str = ".") -> str:
    """Searches for files matching a specific name pattern."""
    args = FileSearchArgs(query=query, directory_path=directory_path)
    try:
        return _search_tool.run({"pattern": args.query, "dir_path": args.directory_path})
    except Exception as e:
        return f"Error searching files: {str(e)}"


@tool(parse_docstring=False)
def read_workspace_file(relative_path: str, max_chars: int = 100_000) -> str:
    """Read a UTF-8 text file relative to the workspace root set by ``init_workspace_root``.

    ``relative_path`` uses forward slashes; ``..`` and absolute paths are rejected.
    """
    if _WORKSPACE_ROOT is None:
        return "Workspace root is not set; call init_workspace_root first."
    parts = [p for p in relative_path.replace("\\", "/").split("/") if p and p != "."]
    if not parts or any(p == ".." for p in parts):
        return "Invalid relative_path (non-empty path under root; no ..)."
    path = safe_resolve_under(_WORKSPACE_ROOT, parts)
    if path is None:
        return "Path escape rejected (must stay under workspace root)."
    return read_text_limited(path, max_chars)


@tool(parse_docstring=False)
def list_workspace_directory(relative_path: str = "", max_entries: int = 80) -> str:
    """List files and subdirectories under ``relative_path`` within the workspace root."""
    if _WORKSPACE_ROOT is None:
        return "Workspace root is not set; call init_workspace_root first."
    rel = (relative_path or "").strip().replace("\\", "/").strip("/")
    parts = [p for p in rel.split("/") if p and p != "."] if rel else []
    if any(p == ".." for p in parts):
        return "Invalid relative_path (no ..)."
    target = safe_resolve_under(_WORKSPACE_ROOT, parts)
    if target is None:
        return "Path escape rejected."
    if not target.is_dir():
        return f"Not a directory: {relative_path or '.'}"
    cap = max(1, min(max_entries, 500))
    all_entries = sorted(target.iterdir(), key=lambda p: p.name)
    slice_ = all_entries[:cap]
    lines = [p.name + ("/" if p.is_dir() else "") for p in slice_]
    return format_dir_listing(lines, len(all_entries) > cap)


__all__ = [
    "copy_file",
    "create_file",
    "delete_file",
    "file_search",
    "init_workspace_root",
    "list_files",
    "list_workspace_directory",
    "move_file",
    "read_file",
    "read_workspace_file",
    "rename_file",
    "write_file",
]
