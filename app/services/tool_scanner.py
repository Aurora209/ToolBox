# File: ToolBox/app/services/tool_scanner.py

import json
import os
from datetime import datetime
from pathlib import Path

from ..utils.size_utils import format_size
from ..utils.type_utils import get_file_type_category

# 修改记录文件路径为应用目录下
RECORD_FILE = Path(__file__).parent.parent.parent / "tools_record.json"


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


def scan_directory(self, directory: Path, category_name: str):
    """扫描目录中的工具文件"""
    tools = []
    supported = {'.exe', '.msi', '.zip', '.rar', '.7z', '.pdf', '.txt', '.bat', '.cmd',
                 '.reg', '.lnk', '.png', '.jpg', '.mp4', '.mp3', '.py', '.docx', '.xlsx', '.pptx'}
    if not directory.exists():
        return tools
    try:
        for p in directory.iterdir():
            if p.is_file() and p.suffix.lower() in supported:
                st = p.stat()
                tool_path = str(p)
                custom_name = self.config.get('ToolInfo', tool_path + '_name', fallback=p.stem)
                note = self.config.get('ToolInfo', tool_path + '_note', fallback='')
                tools.append({
                    'name': custom_name,
                    'path': tool_path,
                    'ext': p.suffix.lower(),
                    'type': get_file_type_category(p.suffix),
                    'size': format_size(st.st_size),
                    'category': category_name,
                    'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d'),
                    'note': note
                })
                record_tool_added(self, tool_path, custom_name, category, note)
    except Exception as e:
        print(f"扫描目录 {directory} 时出错: {e}")
    return sorted(tools, key=lambda x: x['name'].lower())


def scan_directory_for_archives(self, directory: Path, category_name: str):
    """扫描目录中的压缩包文件"""
    archives = []
    exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}
    if not directory.exists():
        return archives
    try:
        for p in directory.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                st = p.stat()
                archives.append({
                    'name': p.stem,
                    'path': str(p),
                    'ext': p.suffix.lower(),
                    'size': format_size(st.st_size),
                    'category': category_name
                })
                record_tool_added(self, str(p), p.stem, category_name)
    except:
        pass
    return archives


def record_tool_added(self, tool_path, tool_name, category, note=""):
    """记录工具添加信息"""
    tool_path = str(Path(tool_path))
    if tool_path in self.tools_added_record:
        return
    
    add_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tool_type = get_file_type_category(Path(tool_path).suffix)
    
    version = "-"
    if hasattr(self, 'get_file_version_info') and self.get_file_version_info and Path(tool_path).suffix.lower() == '.exe':
        version_info = self.get_file_version_info(tool_path)
        if version_info and 'file_version' in version_info:
            version = version_info['file_version']
        else:
            version = "未知"
    
    record_value = f"{tool_name}|{category}|{add_time}|{tool_type}|{note}|{version}"
    self.config['ToolAddedRecord'][tool_path] = record_value
    self.config_manager.save_config()
    
    self.tools_added_record[tool_path] = {
        'name': tool_name,
        'category': category,
        'add_time': add_time,
        'type': tool_type,
        'note': note,
        'version': version
    }