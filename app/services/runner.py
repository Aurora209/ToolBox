# File: ToolBox/app/services/runner.py
import subprocess
import os
import sys
from pathlib import Path

from .archive_service import extract_archive
from .tool_scanner import record_tool_usage

def run_or_extract_tool(self, tool):
    """根据文件类型运行或解压/打开工具。

    - 压缩包（.zip/.rar/.7z/.tar 等）调用解压器 `extract_archive`。
    - 脚本（.py）通过 Python 解释器运行。
    - 其它类型在系统上直接打开（Windows 使用 os.startfile）。
    同时记录使用信息（record_tool_usage）。
    """
    try:
        path = tool['path'] if isinstance(tool, dict) and 'path' in tool else str(tool)
        ext = Path(path).suffix.lower()
        archives = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}

        if ext in archives:
            # 使用 archive_service 提示选择解压目录并解压（GUI 交互）
            extract_archive(self, path)
            return True

        if ext == '.py':
            subprocess.Popen([sys.executable, path])
        else:
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])

        # 记录使用信息（如果提供了 name / category）
        if isinstance(tool, dict):
            name = tool.get('name', Path(path).stem)
            category = tool.get('category', '')
            record_tool_usage(self, path, name, category)
        return True
    except Exception as e:
        print(f"运行或处理工具时发生错误: {e}")
        return False