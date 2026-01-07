# File: ToolBox/app/utils/tool_manager.py

import os
import subprocess
from tkinter import messagebox, filedialog, Toplevel, Frame, Label, Entry, Button, StringVar
from pathlib import Path
from datetime import datetime


def _norm_key(key: str) -> str:
    """统一 ToolAddedRecord 的 key：分隔符 + 小写"""
    return (key or "").replace("/", "\\").strip().lower()


def run_tool(app, path):
    """运行工具，脚本使用当前 Python 解释器，其他文件使用系统默认方式打开（保留 shell 调用以兼容 exe）"""
    if not os.path.exists(path):
        messagebox.showerror("错误", "文件不存在")
        return

    try:
        ext = Path(path).suffix.lower()
        if ext in ('.py', '.pyw'):
            subprocess.Popen([os.sys.executable, path], shell=False)
        else:
            os.startfile(path)

        # 记录使用次数（可选）
        try:
            for tool in getattr(app, 'current_displayed_tools', []) or []:
                if tool.get('path') == path:
                    try:
                        from ..services.tool_scanner import record_tool_usage
                        name = tool.get('name', Path(path).stem)
                        ext_label = tool.get('ext', '')
                        record_tool_usage(app, tool['path'], name + ext_label, tool.get('category', ''))
                    except Exception:
                        pass
                    break
        except Exception:
            pass

    except Exception as e:
        messagebox.showerror("运行失败", str(e))


def open_folder(path):
    """打开工具所在文件夹"""
    folder = os.path.dirname(path)
    try:
        os.startfile(folder)
    except Exception as e:
        messagebox.showerror("打开失败", str(e))


def copy_path(root, path):
    """复制路径到剪贴板"""
    try:
        root.clipboard_clear()
        root.clipboard_append(path)
        root.update()
        messagebox.showinfo("成功", "路径已复制到剪贴板！")
    except Exception as e:
        messagebox.showerror("失败", str(e))


def rename_tool(app, path, current_name):
    """修改工具显示标题（写入 ToolInfo）"""
    win = Toplevel(app.root)
    win.title("修改工具标题")
    win.geometry("420x160")
    win.transient(app.root)
    win.grab_set()

    Label(win, text="工具标题：", font=("Microsoft YaHei", 10)).pack(pady=(18, 6))
    name_var = StringVar(value=current_name or Path(path).stem)
    entry = Entry(win, textvariable=name_var, font=("Microsoft YaHei", 11), width=36)
    entry.pack(padx=16)
    entry.focus_set()

    def save():
        new_name = name_var.get().strip()
        if 'ToolInfo' not in app.config:
            try:
                app.config.add_section('ToolInfo')
            except Exception:
                app.config['ToolInfo'] = {}
        if new_name:
            app.config['ToolInfo'][path + '_name'] = new_name
        else:
            try:
                app.config['ToolInfo'].pop(path + '_name', None)
            except Exception:
                pass
        try:
            app.config_manager.save_config()
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return
        win.destroy()
        try:
            app.refresh_tools()
        except Exception:
            pass

    btn = Frame(win)
    btn.pack(pady=18)
    Button(btn, text="保存", width=10, bg="#27ae60", fg="white", command=save).pack(side="left", padx=8)
    Button(btn, text="取消", width=10, command=win.destroy).pack(side="left", padx=8)

    win.wait_window()


def show_note_editor(root, current_note):
    """显示备注编辑器（支持多行）

    修复点：
    - 始终提供【保存】【取消】按钮
    - 支持 Ctrl+S 保存、Esc 取消
    - 关闭窗口等同于取消（不保存）
    """
    from tkinter import Text, Scrollbar as TkScrollbar

    win = Toplevel(root)
    win.title("编辑工具备注")
    win.geometry("520x420")
    win.transient(root)
    win.grab_set()

    Label(win, text="工具备注（支持多行）", font=("Microsoft YaHei", 12, "bold")).pack(pady=(12, 6))

    text_frame = Frame(win)
    text_frame.pack(fill="both", expand=True, padx=16, pady=8)

    text = Text(text_frame, font=("Microsoft YaHei", 11), wrap="word")
    scrollbar = TkScrollbar(text_frame, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    text.insert("1.0", current_note or "")
    text.focus_set()

    btn_frame = Frame(win)
    btn_frame.pack(fill="x", padx=16, pady=(6, 12))

    result = [None]

    def do_save(_evt=None):
        result[0] = text.get("1.0", "end").rstrip("\n")
        win.destroy()

    def do_cancel(_evt=None):
        result[0] = None
        win.destroy()

    Button(btn_frame, text="保存", width=10, bg="#27ae60", fg="white", command=do_save).pack(side="right", padx=(8, 0))
    Button(btn_frame, text="取消", width=10, command=do_cancel).pack(side="right")

    win.bind("<Control-s>", do_save)
    win.bind("<Escape>", do_cancel)
    win.protocol("WM_DELETE_WINDOW", do_cancel)

    win.wait_window()
    return result[0]


def edit_note(app, path):
    """编辑工具备注（持久化到 ToolInfo + ToolAddedRecord）

    修复点：
    - ToolAddedRecord 分区可能不存在：自动创建
    - ConfigParser 可能把 key lower：统一用 rel_key.lower() 写入与读取
    - 无论 app.tools_added_record 是否已有记录，都尝试更新/创建记录
    """
    path = str(path)

    # 读取旧备注（ToolInfo 使用绝对路径 key）
    try:
        current_note = app.config.get('ToolInfo', {}).get(path + '_note', '')
    except Exception:
        current_note = ''

    note = show_note_editor(app.root, current_note)
    if note is None:
        return
    note = (note or '').strip()

    # 确保 ToolInfo 分区存在
    if 'ToolInfo' not in app.config:
        try:
            app.config.add_section('ToolInfo')
        except Exception:
            app.config['ToolInfo'] = {}

    # 写入 ToolInfo
    if note:
        app.config['ToolInfo'][path + '_note'] = note
    else:
        try:
            app.config['ToolInfo'].pop(path + '_note', None)
        except Exception:
            pass

    # 计算 ToolAddedRecord 的 key：优先 storage 相对路径
    key = path
    try:
        if hasattr(app, 'storage_path') and app.storage_path:
            rel = os.path.relpath(path, app.storage_path)
            if not rel.startswith('..'):
                key = rel
    except Exception:
        pass
    norm_key = _norm_key(key)

    # 确保 ToolAddedRecord 分区存在
    if 'ToolAddedRecord' not in app.config:
        try:
            app.config.add_section('ToolAddedRecord')
        except Exception:
            app.config['ToolAddedRecord'] = {}

    # 确保内存字典存在
    if not hasattr(app, 'tools_added_record') or not isinstance(app.tools_added_record, dict):
        app.tools_added_record = {}

    # 读取已有记录（优先 config，其次内存）
    record_str = ''
    try:
        record_str = app.config['ToolAddedRecord'].get(norm_key, '')
    except Exception:
        record_str = ''

    if not record_str and norm_key in app.tools_added_record:
        r = app.tools_added_record.get(norm_key, {})
        record_str = f"{r.get('name','')}|{r.get('category','')}|{r.get('add_time','')}|{r.get('type','')}|{r.get('note','')}|{r.get('version','')}"

    parts = record_str.split('|', 5) if record_str else []
    if len(parts) != 6:
        # 记录不存在：尽量补齐
        tool_name = Path(path).stem
        tool_category = ''
        tool_type = ''
        add_time = ''
        version = ''
        try:
            for t in getattr(app, 'current_displayed_tools', []) or []:
                if t.get('path') == path:
                    tool_name = t.get('name', tool_name)
                    tool_category = t.get('category', '') or tool_category
                    tool_type = t.get('type', '') or tool_type
                    break
        except Exception:
            pass
        if not tool_type:
            # 简单类型
            ext = Path(path).suffix.lower()
            if ext in ('.exe', '.msi'):
                tool_type = '可执行文件'
            else:
                tool_type = ext.replace('.', '') or '文件'
        parts = [tool_name, tool_category, add_time, tool_type, note, version]
    else:
        parts[4] = note  # 更新备注

    # 写入 config + 内存
    app.config['ToolAddedRecord'][norm_key] = '|'.join(parts)
    app.tools_added_record[norm_key] = {
        'name': parts[0],
        'category': parts[1],
        'add_time': parts[2],
        'type': parts[3],
        'note': parts[4],
        'version': parts[5],
    }

    try:
        app.config_manager.save_config()
    except Exception as e:
        messagebox.showerror("保存失败", str(e))
        return

    try:
        app.refresh_tools()
    except Exception:
        pass


def change_tool_icon(app, tool_path, tool_name):
    """更改工具图标（复制 ico/png 到同目录同名）"""
    filetypes = [("图标文件", "*.ico *.png"), ("ICO 文件", "*.ico"), ("PNG 文件", "*.png"), ("所有文件", "*.*")]
    icon_path = filedialog.askopenfilename(title="选择自定义图标", filetypes=filetypes)
    if not icon_path:
        return

    tool_dir = Path(tool_path).parent
    tool_stem = Path(tool_path).stem

    for ext in ['.ico', '.png']:
        old_icon = tool_dir / f"{tool_stem}{ext}"
        if old_icon.exists():
            try:
                old_icon.unlink()
            except Exception as exc:
                print(f"删除旧图标失败: {old_icon} ({exc})")

    ext = Path(icon_path).suffix.lower()
    target_path = tool_dir / f"{tool_stem}{ext}"
    try:
        from shutil import copyfile
        copyfile(icon_path, target_path)
        messagebox.showinfo("成功", "图标已更新！\n刷新后生效")
        try:
            app.refresh_tools()
        except Exception:
            pass
    except Exception as e:
        messagebox.showerror("失败", f"图标更新失败：{e}")


def delete_tool(app, path, name):
    """删除工具（删除文件 + 清理配置项 + 清理 ToolAddedRecord）"""
    if not messagebox.askyesno("确认删除", f"确定删除：{name}？\n\n{path}"):
        return

    try:
        if os.path.exists(path):
            os.remove(path)

        # 清理自定义图标
        tool_dir = Path(path).parent
        tool_stem = Path(path).stem
        for ext in ['.ico', '.png']:
            custom_icon = tool_dir / f"{tool_stem}{ext}"
            if custom_icon.exists():
                try:
                    custom_icon.unlink()
                except Exception as exc:
                    print(f"删除自定义图标失败: {custom_icon} ({exc})")

        # 清理 ToolInfo
        if 'ToolInfo' in app.config:
            app.config['ToolInfo'].pop(path + '_name', None)
            app.config['ToolInfo'].pop(path + '_note', None)

        # 清理 ToolAddedRecord（支持相对/绝对 + 统一 norm）
        key = path
        try:
            if hasattr(app, 'storage_path') and app.storage_path:
                rel = os.path.relpath(path, app.storage_path)
                if not rel.startswith('..'):
                    key = rel
        except Exception:
            pass
        norm_key = _norm_key(key)

        if 'ToolAddedRecord' in app.config:
            try:
                app.config['ToolAddedRecord'].pop(norm_key, None)
            except Exception:
                pass

        if hasattr(app, 'tools_added_record') and isinstance(app.tools_added_record, dict):
            app.tools_added_record.pop(norm_key, None)

        app.config_manager.save_config()

        messagebox.showinfo("成功", "删除完成！")
        try:
            app.refresh_tools()
        except Exception:
            pass
    except Exception as e:
        messagebox.showerror("删除失败", str(e))
