import json
import os
from datetime import datetime
from pathlib import Path

from ..utils.size_utils import format_size
from ..utils.type_utils import get_file_type_category

RECORD_FILE = Path(__file__).parent.parent.parent / "tools_record.json"


def _norm_key(key: str) -> str:
    """统一 ToolAddedRecord 的 key：分隔符 + 小写"""
    return (key or "").replace("/", "\\").strip().lower()


def _resolve_record_abs_path(app, record_key: str) -> str:
    """
    将 ToolAddedRecord 的 key 解析为绝对路径：

    规则（关键修复点）：
    - 若 key 是绝对路径（含盘符/UNC）：直接返回该绝对路径（用于判断是否“越界”）
    - 若 key 是相对路径：只能拼到 storage_path 下；如果拼出来不在 storage 内，返回空字符串
    """
    k = (record_key or "").strip()
    if not k:
        return ""

    # 绝对路径（Windows）
    if (len(k) >= 2 and k[1] == ":") or k.startswith("\\\\"):
        return os.path.normpath(os.path.abspath(k))

    storage = getattr(app, "storage_path", None)
    if not storage:
        return ""

    storage_abs = os.path.abspath(str(storage))
    abs_path = os.path.normpath(os.path.abspath(os.path.join(storage_abs, k)))

    # 🔒 关键：相对 key 拼出来必须仍在 storage 内
    try:
        if os.path.commonpath([storage_abs, abs_path]) != storage_abs:
            return ""
    except Exception:
        return ""

    return abs_path


def prune_missing_tool_records(app):
    """
    清理所有“文件已不存在”的记录，或“越界（不在 Storage 内）”的记录：
    - ToolAddedRecord（ini）
    - tools_added_record（内存）
    - ToolInfo（ini，按绝对路径 key）
    - tools_record.json（使用记录）
    """
    storage = getattr(app, "storage_path", None)
    storage_abs = os.path.abspath(str(storage)) if storage else None

    to_remove_keys = []

    # 1) config 中的 ToolAddedRecord
    try:
        if hasattr(app, "config") and "ToolAddedRecord" in app.config:
            sec = app.config["ToolAddedRecord"]
            for raw_key in list(sec.keys()):
                abs_path = _resolve_record_abs_path(app, raw_key)

                # ✅ 若 abs_path 为空：说明相对 key 拼接越界，直接删
                if not abs_path:
                    to_remove_keys.append(raw_key)
                    continue

                # ✅ 绝对路径越界：不在 Storage 内，也删
                if storage_abs:
                    try:
                        if os.path.commonpath([storage_abs, abs_path]) != storage_abs:
                            to_remove_keys.append(raw_key)
                            continue
                    except Exception:
                        to_remove_keys.append(raw_key)
                        continue

                # ✅ 文件不存在：删
                if not os.path.exists(abs_path):
                    to_remove_keys.append(raw_key)
    except Exception as e:
        print(f"prune_missing_tool_records: 遍历 ToolAddedRecord 失败: {e}")

    # 2) 内存 tools_added_record
    try:
        tar = getattr(app, "tools_added_record", None)
        if isinstance(tar, dict):
            for raw_key in list(tar.keys()):
                abs_path = _resolve_record_abs_path(app, raw_key)

                if not abs_path:
                    if raw_key not in to_remove_keys:
                        to_remove_keys.append(raw_key)
                    continue

                if storage_abs:
                    try:
                        if os.path.commonpath([storage_abs, abs_path]) != storage_abs:
                            if raw_key not in to_remove_keys:
                                to_remove_keys.append(raw_key)
                            continue
                    except Exception:
                        if raw_key not in to_remove_keys:
                            to_remove_keys.append(raw_key)
                        continue

                if not os.path.exists(abs_path):
                    if raw_key not in to_remove_keys:
                        to_remove_keys.append(raw_key)
    except Exception:
        pass

    if not to_remove_keys:
        return

    # 3) 删除 ToolAddedRecord / 内存 tools_added_record
    try:
        if hasattr(app, "config") and "ToolAddedRecord" in app.config:
            sec = app.config["ToolAddedRecord"]
            for k in to_remove_keys:
                sec.pop(k, None)
                sec.pop(_norm_key(k), None)
    except Exception as e:
        print(f"prune_missing_tool_records: 删除 ToolAddedRecord 失败: {e}")

    try:
        tar = getattr(app, "tools_added_record", None)
        if isinstance(tar, dict):
            for k in to_remove_keys:
                tar.pop(k, None)
                tar.pop(_norm_key(k), None)
    except Exception:
        pass

    # 4) 删除 ToolInfo（绝对路径 key：path_name / path_note）
    try:
        if hasattr(app, "config") and "ToolInfo" in app.config:
            info = app.config["ToolInfo"]
            for k in to_remove_keys:
                abs_path = _resolve_record_abs_path(app, k)
                if abs_path:
                    info.pop(abs_path + "_name", None)
                    info.pop(abs_path + "_note", None)
    except Exception as e:
        print(f"prune_missing_tool_records: 删除 ToolInfo 失败: {e}")

    # 5) 删除 tools_record.json 中 path 指向不存在/越界的记录
    try:
        tr = getattr(app, "tools_record", None)
        if isinstance(tr, dict) and tr:
            dead = []
            for rk, rv in tr.items():
                p = ""
                try:
                    p = rv.get("path", "")
                except Exception:
                    p = ""
                if not p:
                    continue

                abs_p = os.path.abspath(os.path.normpath(p))

                # 不在 Storage 内 -> 删
                if storage_abs:
                    try:
                        if os.path.commonpath([storage_abs, abs_p]) != storage_abs:
                            dead.append(rk)
                            continue
                    except Exception:
                        dead.append(rk)
                        continue

                # 不存在 -> 删
                if not os.path.exists(abs_p):
                    dead.append(rk)

            for rk in dead:
                tr.pop(rk, None)
    except Exception:
        pass

    # 6) 保存 ini + tools_record.json
    try:
        if hasattr(app, "config_manager"):
            app.config_manager.save_config()
    except Exception as e:
        print(f"prune_missing_tool_records: 保存 ini 失败: {e}")

    try:
        save_tools_record(app)
    except Exception:
        pass

    print(f"prune_missing_tool_records: 已清理 {len(to_remove_keys)} 条不存在/越界文件的记录")


def load_tools_record(app):
    """加载工具使用记录（tools_record.json），并清理孤儿记录"""
    app.tools_record = {}
    app.record_file = RECORD_FILE

    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                app.tools_record = json.load(f)
        except Exception as e:
            print(f"加载工具记录失败: {e}")
            app.tools_record = {}

    # ✅ 启动时清理
    try:
        prune_missing_tool_records(app)
    except Exception:
        pass


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
    """扫描目录中的工具文件（只扫描传入目录）"""
    tools = []
    supported = {
        ".exe", ".msi", ".zip", ".rar", ".7z", ".pdf", ".txt",
        ".bat", ".cmd", ".reg", ".lnk", ".png", ".jpg", ".jpeg",
        ".mp4", ".mp3", ".py", ".pyw", ".docx", ".xlsx", ".pptx"
    }

    if not directory.exists():
        return tools

    try:
        for p in directory.iterdir():
            if p.is_file() and p.suffix.lower() in supported:
                st = p.stat()
                tool_path = str(p)

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

                record_tool_added(self, tool_path, custom_name, category_name, note)

    except Exception as e:
        print(f"扫描目录 {directory} 时出错: {e}")

    tools = sorted(tools, key=lambda x: x["name"].lower())

    # ✅ 每次扫描后清理一次（孤儿/越界记录）
    try:
        prune_missing_tool_records(self)
    except Exception:
        pass

    return tools


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
    """记录工具添加信息（ToolAddedRecord + 内存 tools_added_record）"""
    tool_path = str(Path(tool_path))

    if not hasattr(self, "tools_added_record") or not isinstance(self.tools_added_record, dict):
        self.tools_added_record = {}

    # key：优先相对 storage_path（这样天然锚定 Storage）
    key = tool_path
    try:
        if hasattr(self, "storage_path") and self.storage_path:
            rel = os.path.relpath(tool_path, self.storage_path)
            if not rel.startswith(".."):
                key = rel
    except Exception:
        pass

    norm_key = _norm_key(key)

    if norm_key in self.tools_added_record:
        return

    add_time = None
    try:
        if os.path.exists(tool_path):
            ct = os.path.getctime(tool_path)
            add_time = datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        add_time = None
    if not add_time:
        add_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    self.tools_added_record[norm_key] = {
        "name": tool_name,
        "category": category,
        "add_time": add_time,
        "type": tool_type,
        "note": note,
        "version": version
    }

    # 确保分区存在
    try:
        if "ToolAddedRecord" not in self.config:
            try:
                self.config.add_section("ToolAddedRecord")
            except Exception:
                self.config["ToolAddedRecord"] = {}
    except Exception:
        pass

    try:
        self.config["ToolAddedRecord"][norm_key] = f"{tool_name}|{category}|{add_time}|{tool_type}|{note}|{version}"
        self.config_manager.save_config()
    except Exception as e:
        print(f"record_tool_added: 保存配置失败: {e}")
