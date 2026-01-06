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
    except Exception as exc:
        print(f"扫描压缩包目录 {directory} 时出错: {exc}")
    return archives


def record_tool_added(self, tool_path, tool_name, category, note=""):
    """记录工具添加信息。

    保存和内存中的 key 均使用相对于 storage_path 的路径（如果可能），以便移动工具箱目录时记录仍然有效。
    """
    tool_path = str(Path(tool_path))

    # 计算相对于 storage 的 key（回退到绝对路径作为兜底）
    key = tool_path
    try:
        if hasattr(self, 'storage_path') and self.storage_path:
            rel = os.path.relpath(tool_path, self.storage_path)
            if not rel.startswith('..'):
                key = rel
    except Exception:
        pass

    if key in self.tools_added_record:
        return

    # 尝试使用文件创建时间（Windows 上为复制时间）作为添加时间；回退到当前时间
    add_time = None
    try:
        if os.path.exists(tool_path):
            ct = os.path.getctime(tool_path)
            from datetime import datetime as _dt
            add_time = _dt.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        add_time = None

    if not add_time:
        add_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    tool_type = get_file_type_category(Path(tool_path).suffix)

    # 版本信息：优先从文件元数据中读取（支持 exe / msi），否则标注为未知
    version = "-"
    try:
        suffix = Path(tool_path).suffix.lower()
        if suffix in ('.exe', '.msi') and hasattr(self, 'get_file_version_info') and self.get_file_version_info:
            try:
                version_info = self.get_file_version_info(tool_path)
                if version_info and 'file_version' in version_info:
                    version = version_info['file_version']
                elif version_info and 'product_version' in version_info:
                    version = version_info.get('product_version')
                else:
                    version = "未知"
            except Exception:
                version = "未知"
    except Exception:
        version = "-"

    record_value = f"{tool_name}|{category}|{add_time}|{tool_type}|{note}|{version}"
    self.config['ToolAddedRecord'][key] = record_value
    self.config_manager.save_config()

    self.tools_added_record[key] = {
        'name': tool_name,
        'category': category,
        'add_time': add_time,
        'type': tool_type,
        'note': note,
        'version': version
    }

    # 调试：打印创建记录的 key 与基本信息，确保内存更新
    try:
        print(f"record_tool_added: key={key}, version={version}, add_time={add_time}")
    except Exception:
        pass

    # 兼容：若配置中不存在该 key，则写入配置以便持久化
    try:
        if key not in self.config['ToolAddedRecord']:
            self.config['ToolAddedRecord'][key] = f"{tool_name}|{category}|{add_time}|{tool_type}|{note}|{version}"
            self.config_manager.save_config()
            print(f"record_tool_added: 已写入配置 key={key}")
    except Exception as e:
        print(f"record_tool_added: 保存配置失败: {e}")
