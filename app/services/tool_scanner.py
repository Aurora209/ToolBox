# File: ToolBox/app/services/tool_scanner.py

import json
import os
from datetime import datetime
from pathlib import Path

RECORD_FILE = "tools_record.json"

def load_tools_record(app):
    """加载工具记录"""
    app.tools_record = {}  # {key: record_dict}
    app.record_file = RECORD_FILE
    
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, 'r', encoding='utf-8') as f:
                app.tools_record = json.load(f)
        except Exception as e:
            print(f"加载工具记录失败: {e}")
            app.tools_record = {}

def save_tools_record(app):
    """保存工具记录"""
    try:
        with open(app.record_file, 'w', encoding='utf-8') as f:
            json.dump(app.tools_record, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存工具记录失败: {e}")

def record_tool_usage(app, tool_path, tool_name, category):
    """记录或更新工具使用"""
    key = f"{category}/{tool_name}"
    
    if key not in app.tools_record:
        app.tools_record[key] = {
            "name": tool_name,
            "category": category,
            "path": tool_path,
            "first_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_used": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usage_count": 1
        }
    else:
        app.tools_record[key]["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app.tools_record[key]["usage_count"] += 1
    
    save_tools_record(app)