import json
import os
from datetime import datetime
from pathlib import Path

from ..utils.size_utils import format_size
from ..utils.type_utils import get_file_type_category

# 修改记录文件路径为应用目录下
RECORD_FILE = Path(__file__).parent.parent.parent / "tools_record.json"


def _norm_key(key: str) -> str:
    """统一 ToolAddedRecord 的 key：分隔符 + 小写（避免 configparser/大小写导致查不到）"""
    return (key or "").replace("/", "\\").strip().lower()


def load_tools_record(app):
    """加载工具使用记录（tools_record.json）"""
    app.tools_record = {}  # {key: record_dict}
    app.record_file = RECORD_FILE

    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                app.tools_record = json.load(f)
        except Exception as e:
            print(f"加载工具记录失败: {e}")
            app.tools_record = {}


def save_tools_record(app):
    """保存工具使用记录"""
    record_path = getattr(app, "record_file", None) or RECORD_FILE
    try:
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(app.tools_record, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存工具记录失败: {e}")


def record_tool_usage(app, tool_path, tool_name, category):
    """记录或更新工具使用次数"""
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
    supported = {
        ".exe", ".msi", ".zip", ".rar", ".7z", ".pdf", ".txt",
        ".bat", ".cmd", ".reg", ".lnk", ".png", ".jpg", ".mp4",
        ".mp3", ".py", ".docx", ".xlsx", ".pptx"
    }

    if not directory.exists():
        return tools

    try:
        for p in directory.iterdir():
            if p.is_file() and p.suffix.lower() in supported:
                st = p.stat()
                tool_path = str(p)

                # 自定义标题/备注（ToolInfo 用绝对路径）
                custom_name = self.config.get("ToolInfo", tool_path + "_name", fallback=p.stem)
                note = self.config.get("ToolInfo", tool_path + "_note", fallback="")

                tools.append({
                    "name": custom_name,
                    "path": tool_path,
                    "ext": p.suffix.lower(),
                    "type": get_file_type_category(p.suffix),
                    "size": format_size(st.st_size),
                    "category": category_name,
                    "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                    "note": note
                })

                # 记录添加信息（注意：category 要用 category_name）
                record_tool_added(self, tool_path, custom_name, category_name, note)

    except Exception as e:
        print(f"扫描目录 {directory} 时出错: {e}")

    return sorted(tools, key=lambda x: x["name"].lower())


def scan_directory_for_archives(self, directory: Path, category_name: str):
    """扫描目录中的压缩包文件"""
    archives = []
    exts = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}

    if not directory.exists():
        return archives

    try:
        for p in directory.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                st = p.stat()
                archives.append({
                    "name": p.stem,
                    "path": str(p),
                    "ext": p.suffix.lower(),
                    "size": format_size(st.st_size),
                    "category": category_name
                })
    except Exception as e:
        print(f"扫描目录 {directory} 时出错: {e}")

    return sorted(archives, key=lambda x: x["name"].lower())


def record_tool_added(self, tool_path, tool_name, category, note=""):
    """记录工具添加信息（ToolAddedRecord + 内存 tools_added_record）

    修复点：
    - 保证 ToolAddedRecord 分区存在（否则会抛 KeyError 或保存失败）
    - key 统一为 “相对 storage_path 的路径 + 小写”，避免大小写导致查不到版本/添加时间/备注
    """
    tool_path = str(Path(tool_path))

    # 确保内存字典存在
    if not hasattr(self, "tools_added_record") or not isinstance(self.tools_added_record, dict):
        self.tools_added_record = {}

    # 计算相对 storage 的 key（回退到绝对路径）
    key = tool_path
    try:
        if hasattr(self, "storage_path") and self.storage_path:
            rel = os.path.relpath(tool_path, self.storage_path)
            if not rel.startswith(".."):
                key = rel
    except Exception:
        pass

    norm_key = _norm_key(key)

    # 已有记录就不重复写
    if norm_key in self.tools_added_record:
        return

    # 添加时间：优先用文件创建时间，否则当前时间
    add_time = None
    try:
        if os.path.exists(tool_path):
            ct = os.path.getctime(tool_path)
            add_time = datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        add_time = None

    if not add_time:
        add_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 类型/版本
    suffix = Path(tool_path).suffix.lower()
    tool_type = get_file_type_category(suffix)

    version = "-"
    try:
        if suffix in (".exe", ".msi") and hasattr(self, "get_file_version_info") and self.get_file_version_info:
            info = self.get_file_version_info(tool_path)
            if info and info.get("file_version"):
                version = info["file_version"]
            elif info and info.get("product_version"):
                version = info["product_version"]
            else:
                version = "未知"
    except Exception:
        version = "未知"

    # 写内存
    self.tools_added_record[norm_key] = {
        "name": tool_name,
        "category": category,
        "add_time": add_time,
        "type": tool_type,
        "note": note,
        "version": version
    }

    # 确保配置分区存在
    try:
        if "ToolAddedRecord" not in self.config:
            try:
                self.config.add_section("ToolAddedRecord")
            except Exception:
                self.config["ToolAddedRecord"] = {}
    except Exception:
        pass

    # 写配置（覆盖写入最安全）
    try:
        self.config["ToolAddedRecord"][norm_key] = f"{tool_name}|{category}|{add_time}|{tool_type}|{note}|{version}"
        self.config_manager.save_config()
    except Exception as e:
        print(f"record_tool_added: 保存配置失败: {e}")
