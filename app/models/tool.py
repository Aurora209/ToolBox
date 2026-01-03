# File: ToolBox/app/models/tool.py
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    path: str
    ext: str
    type: str
    size: str
    category: str
    mtime: str
    full_path: str