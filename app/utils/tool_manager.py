import os
import subprocess
from tkinter import messagebox, filedialog, Toplevel, Frame, Label, Entry, Button, StringVar
from pathlib import Path


def _norm_key(key: str) -> str:
    return (key or "").replace("/", "\\").strip().lower()


def _get_rel_key(app, abs_path: str) -> str:
    """优先用相对 storage_path 的 key"""
    abs_path = str(abs_path)
    try:
        storage = getattr(app, "storage_path", None)
        if storage:
            rel = os.path.relpath(abs_path, str(storage))
            if not rel.startswith(".."):
                return rel
    except Exception:
        pass
    return abs_path


def _cleanup_records_for_path(app, abs_path: str):
    """同步清理三处记录：ToolAddedRecord + ToolInfo + tools_record.json"""
    abs_path = os.path.normpath(str(abs_path))
    rel_key = _get_rel_key(app, abs_path)
    k1 = _norm_key(rel_key)
    k2 = _norm_key(abs_path)

    # 1) ToolAddedRecord（ini）
    try:
        if hasattr(app, "config") and "ToolAddedRecord" in app.config:
            sec = app.config["ToolAddedRecord"]
            sec.pop(k1, None)
            sec.pop(k2, None)
            # 兼容原始未 lower 的情况
            sec.pop(rel_key, None)
            sec.pop(abs_path, None)
    except Exception:
        pass

    # 2) tools_added_record（内存）
    try:
        tar = getattr(app, "tools_added_record", None)
        if isinstance(tar, dict):
            tar.pop(k1, None)
            tar.pop(k2, None)
            tar.pop(rel_key, None)
            tar.pop(abs_path, None)
    except Exception:
        pass

    # 3) ToolInfo（ini：绝对路径 key）
    try:
        if hasattr(app, "config") and "ToolInfo" in app.config:
            info = app.config["ToolInfo"]
            info.pop(abs_path + "_name", None)
            info.pop(abs_path + "_note", None)
    except Exception:
        pass

    # 4) tools_record.json（使用记录：按 path 匹配删除）
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
                if p and os.path.normpath(p) == abs_path:
                    dead.append(rk)
            for rk in dead:
                tr.pop(rk, None)

            # 写回 json
            try:
                from ..services.tool_scanner import save_tools_record
                save_tools_record(app)
            except Exception:
                pass
    except Exception:
        pass

    # 保存 ini
    try:
        if hasattr(app, "config_manager"):
            app.config_manager.save_config()
    except Exception:
        pass


def run_tool(app, path):
    """运行工具"""
    if not os.path.exists(path):
        # ✅ 文件不存在：顺手清理记录（用户可能手动删了文件）
        _cleanup_records_for_path(app, path)
        messagebox.showerror("错误", "文件不存在，已清理对应记录。")
        try:
            app.refresh_tools()
        except Exception:
            pass
        return

    try:
        ext = Path(path).suffix.lower()
        if ext in ('.py', '.pyw'):
            subprocess.Popen([os.sys.executable, path], shell=False)
        else:
            os.startfile(path)
    except Exception as e:
        messagebox.showerror("运行失败", str(e))


def open_folder(path):
    folder = os.path.dirname(path)
    try:
        os.startfile(folder)
    except Exception as e:
        messagebox.showerror("打开失败", str(e))


def copy_path(root, path):
    try:
        root.clipboard_clear()
        root.clipboard_append(path)
        root.update()
        messagebox.showinfo("成功", "路径已复制到剪贴板！")
    except Exception as e:
        messagebox.showerror("失败", str(e))


def delete_tool(app, path, name):
    """删除工具（文件 + 记录同步删除）"""
    if not messagebox.askyesno("确认删除", f"确定删除：{name}？\n\n{path}"):
        return

    abs_path = os.path.normpath(str(path))

    # 先尝试删文件
    file_deleted = False
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
            file_deleted = True
    except Exception as e:
        messagebox.showerror("删除失败", str(e))
        # 即便文件未删掉，也继续尝试清理记录（避免记录脏）
        file_deleted = False

    # 同步清理记录
    _cleanup_records_for_path(app, abs_path)

    # 删除自定义图标（同名 .ico/.png）
    try:
        tool_dir = Path(abs_path).parent
        tool_stem = Path(abs_path).stem
        for ext in ['.ico', '.png']:
            custom_icon = tool_dir / f"{tool_stem}{ext}"
            if custom_icon.exists():
                try:
                    custom_icon.unlink()
                except Exception:
                    pass
    except Exception:
        pass

    try:
        app.refresh_tools()
    except Exception:
        pass

    if file_deleted:
        messagebox.showinfo("成功", "工具已删除，记录已同步清理。")
    else:
        messagebox.showinfo("提示", "文件删除可能失败，但记录已同步清理。")
