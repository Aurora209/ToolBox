# File: ToolBox/app/services/category_service.py

import os
from pathlib import Path

from ..utils.type_utils import get_file_type_category

# ✅ 分类刷新前清理孤儿记录
try:
    from .tool_scanner import prune_missing_tool_records
except Exception:
    prune_missing_tool_records = None


def _get_supported_exts(app):
    """支持的工具后缀：优先用 app.supported_extensions，没有就给默认集合"""
    exts = getattr(app, "supported_extensions", None)
    if isinstance(exts, (set, list, tuple)) and exts:
        return set(str(x).lower() for x in exts)

    return {
        ".exe", ".msi", ".zip", ".rar", ".7z", ".pdf", ".txt",
        ".bat", ".cmd", ".reg", ".lnk", ".png", ".jpg", ".jpeg",
        ".mp4", ".mp3", ".py", ".pyw", ".docx", ".xlsx", ".pptx"
    }


def _format_category(rel_path: str) -> str:
    """把 1\\11 转为 1 > 11"""
    rel_path = (rel_path or ".").replace("/", os.sep).replace("\\", os.sep)
    parts = [p for p in rel_path.split(os.sep) if p and p != "."]
    return " > ".join(parts) if parts else "所有工具"


def _resolve_under_storage(storage_path: str, path: str) -> str:
    """
    🔒 强制把任何路径钉死在 storage_path 下：
    - 如果 path 在 storage 下：返回 path
    - 否则：回退为 storage_path
    """
    try:
        storage = os.path.abspath(storage_path)
        p = os.path.abspath(path)
        if os.path.commonpath([storage, p]) == storage:
            return p
    except Exception:
        pass
    return os.path.abspath(storage_path)


def get_subcategories_for_category(app, cat_id):
    """
    从配置 [Subcategories] 读取某个主分类的子分类列表。
    约定：key 形如 1_1 = 11, 1_2 = 12 ...
    返回：['11', '12', ...]
    """
    result = []
    try:
        if "Subcategories" not in app.config:
            return result

        sec = app.config["Subcategories"]
        prefix = f"{cat_id}_"

        pairs = []
        for k in sec.keys():
            if not k.startswith(prefix):
                continue
            try:
                idx = int(k.split("_", 1)[1])
            except Exception:
                idx = 999999
            pairs.append((idx, sec.get(k)))

        pairs.sort(key=lambda x: x[0])
        result = [v for _, v in pairs if v]
    except Exception:
        return []
    return result


def get_current_scan_info(app):
    """
    给拖拽/复制等逻辑使用：
    返回 (dir_path, display_name, is_all)
    """
    storage = getattr(app, "storage_path", None)

    if getattr(app, "showing_all_tools", False):
        return storage, "所有工具", True

    sel = getattr(app, "selected_category_path", None) or storage

    display_name = "所有工具"
    try:
        if storage and sel:
            rel = os.path.relpath(str(sel), str(storage))
            display_name = _format_category(rel)
        else:
            display_name = str(sel) if sel else "所有工具"
    except Exception:
        display_name = str(sel) if sel else "所有工具"

    return str(sel), display_name, False


def _build_tool_item(app, file_path: Path, rel_category_path: str):
    """构造单个工具 dict（尽量使用 ToolInfo 自定义标题/备注）"""
    tool_path = str(file_path)
    ext = file_path.suffix.lower()

    # ToolInfo 用绝对路径 key
    name = file_path.stem
    note = ""
    try:
        if hasattr(app, "config") and "ToolInfo" in app.config:
            name = app.config["ToolInfo"].get(tool_path + "_name", name)
            note = app.config["ToolInfo"].get(tool_path + "_note", "")
    except Exception:
        pass

    try:
        typ = get_file_type_category(ext)
    except Exception:
        typ = ext.replace(".", "") or "文件"

    return {
        "name": name,
        "path": tool_path,
        "ext": ext,
        "type": typ,
        "category": _format_category(rel_category_path),
        "note": note,
    }


def _scan_one_dir(app, dir_path: Path, rel_category_path: str):
    """只扫描当前目录（不递归）"""
    tools = []
    if not dir_path.exists() or not dir_path.is_dir():
        return tools

    supported = _get_supported_exts(app)

    try:
        for p in dir_path.iterdir():
            if p.is_file() and p.suffix.lower() in supported and p.name != "__init__.py":
                tools.append(_build_tool_item(app, p, rel_category_path))
    except Exception as e:
        print(f"_scan_one_dir 扫描失败: {dir_path} -> {e}")

    tools.sort(key=lambda x: x.get("name", "").lower())
    return tools


def _apply_search_and_type_filter(app, tools):
    """应用搜索与类型过滤（如果 UI 里有 search_var / filetype_var）"""
    qv = getattr(app, "search_var", None)
    if qv is not None:
        q = (qv.get() or "").strip().lower()
        if q:
            def hit(t):
                return (
                    q in (t.get("name", "") or "").lower()
                    or q in (t.get("note", "") or "").lower()
                    or q in (t.get("path", "") or "").lower()
                )
            tools = [t for t in tools if hit(t)]

    tv = getattr(app, "filetype_var", None)
    if tv is not None:
        selected = tv.get()
        if selected and selected != "全部":
            tools = [t for t in tools if t.get("type") == selected]

    return tools


def load_and_display_tools(app, selected_category_path: str):
    """
    ✅ 点击分类树即清孤儿记录
    ✅ 路径强制限制在 Storage 下（不会跑到盘符根）
    ✅ 一级分类：汇总其下所有二级目录工具（只扫二级，不递归更深）
    ✅ 二级分类：仅显示当前目录工具
    """
    # ✅ 关键：刷新前清理孤儿记录
    try:
        if prune_missing_tool_records:
            prune_missing_tool_records(app)
    except Exception as e:
        print(f"load_and_display_tools: prune_missing_tool_records 失败: {e}")

    if not getattr(app, "storage_path", None):
        return

    # 🔒 强制以 Storage 为唯一根
    storage_path = os.path.abspath(app.storage_path)
    selected_category_path = selected_category_path or storage_path
    selected_category_path = _resolve_under_storage(storage_path, selected_category_path)

    base = Path(storage_path)
    sel = Path(selected_category_path)

    # 相对路径（用于“分类”列显示）
    try:
        rel = os.path.relpath(str(sel), str(base))
    except Exception:
        rel = "."

    # 层级：优先使用 category_manager 设置的 depth
    depth = getattr(app, "selected_category_depth", None)
    if depth not in (1, 2):
        if rel == ".":
            depth = 0
        else:
            parts = [p for p in rel.replace("/", os.sep).replace("\\", os.sep).split(os.sep) if p]
            depth = len(parts)

    tools = []

    if depth == 1:
        # ✅ 一级：汇总一级目录内文件 + 所有二级文件夹内文件（只一层）
        tools.extend(_scan_one_dir(app, sel, rel))
        try:
            subdirs = [p for p in sel.iterdir() if p.is_dir()]
            subdirs.sort(key=lambda x: x.name.lower())
            for sd in subdirs:
                sub_rel = os.path.join(rel, sd.name)
                tools.extend(_scan_one_dir(app, sd, sub_rel))
        except Exception as e:
            print(f"一级分类汇总扫描失败: {sel} -> {e}")
        category_name = _format_category(rel)
    else:
        # ✅ 二级（或更深）：只显示当前目录
        tools = _scan_one_dir(app, sel, rel)
        category_name = _format_category(rel)

    tools = _apply_search_and_type_filter(app, tools)

    try:
        app.current_displayed_tools = tools
    except Exception:
        pass

    app.display_tools_grid(tools, category_name, len(tools))


def load_and_display_all_tools(app):
    """显示所有工具：递归扫描 Storage；刷新前也清理孤儿记录"""
    try:
        if prune_missing_tool_records:
            prune_missing_tool_records(app)
    except Exception as e:
        print(f"load_and_display_all_tools: prune_missing_tool_records 失败: {e}")

    if not getattr(app, "storage_path", None):
        return

    storage_path = os.path.abspath(app.storage_path)
    base = Path(storage_path)
    supported = _get_supported_exts(app)

    tools = []
    try:
        for root, _dirs, files in os.walk(str(base)):
            root_p = Path(root)
            rel = os.path.relpath(root, str(base))
            for fn in files:
                p = root_p / fn
                if p.is_file() and p.suffix.lower() in supported and p.name != "__init__.py":
                    tools.append(_build_tool_item(app, p, rel))
    except Exception as e:
        print(f"load_and_display_all_tools 扫描失败: {e}")

    tools.sort(key=lambda x: (x.get("category", ""), x.get("name", "").lower()))
    tools = _apply_search_and_type_filter(app, tools)

    try:
        app.current_displayed_tools = tools
    except Exception:
        pass

    app.display_tools_grid(tools, "所有工具", len(tools))
