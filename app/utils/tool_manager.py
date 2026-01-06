# File: ToolBox/app/utils/tool_manager.py

import os
import subprocess
from tkinter import messagebox, filedialog, Toplevel, Frame, Label, Entry, Button, StringVar
from pathlib import Path
from datetime import datetime

def run_tool(app, path):
    """运行工具，脚本使用当前 Python 解释器，其他文件使用系统默认方式打开（保留 shell 调用以兼容 exe）"""
    if not os.path.exists(path):
        messagebox.showerror("错误", "文件不存在")
        return

    try:
        ext = Path(path).suffix.lower()
        if ext == '.py':
            import sys
            subprocess.Popen([sys.executable, path])
        else:
            # 对 exe 等直接使用 shell 打开，保留兼容性
            subprocess.Popen(path, shell=True)

        for tool in getattr(app, 'current_displayed_tools', []):
            if tool.get('path') == path:
                try:
                    from ..services.tool_scanner import record_tool_usage
                    name = tool.get('name', Path(path).stem)
                    ext_label = tool.get('ext', '')
                    record_tool_usage(app, tool['path'], name + ext_label, tool.get('category', ''))
                except Exception:
                    pass
                break
    except Exception as e:
        messagebox.showerror("运行失败", str(e))

def open_folder(path):
    """打开工具所在文件夹"""
    folder = os.path.dirname(path)
    if os.path.exists(folder):
        os.startfile(folder)
    else:
        messagebox.showerror("错误", "文件夹不存在")

def copy_path(root, path):
    """复制文件路径到剪贴板"""
    root.clipboard_clear()
    root.clipboard_append(path)
    root.update()
    messagebox.showinfo("成功", f"文件路径已复制：\n{path}")

def rename_tool(app, path, current_name):
    """重命名工具"""
    new_name = simple_input(app.root, "修改工具标题", current_name)
    if new_name and new_name != current_name:
        app.config['ToolInfo'][path + '_name'] = new_name
        app.config_manager.save_config()
        # 兼容：支持相对 storage_path 的 key 或绝对路径
        key = path
        try:
            if hasattr(app, 'storage_path'):
                rel = os.path.relpath(path, app.storage_path)
                if not rel.startswith('..'):
                    key = rel
        except Exception:
            pass

        if key in app.tools_added_record:
            app.tools_added_record[key]['name'] = new_name
            # 同步配置中的记录（优先使用规范化后的 key）
            if key in app.config['ToolAddedRecord']:
                app.config['ToolAddedRecord'][key] = app.config['ToolAddedRecord'][key].replace(current_name, new_name, 1)
            elif path in app.config['ToolAddedRecord']:
                app.config['ToolAddedRecord'][path] = app.config['ToolAddedRecord'][path].replace(current_name, new_name, 1)
            app.config_manager.save_config()
            messagebox.showinfo("成功", f"工具标题已修改为：{new_name}")
            app.refresh_tools()

def edit_note(app, path):
    """编辑工具备注"""
    current_note = app.config['ToolInfo'].get(path + '_note', '')
    note = show_note_editor(app.root, current_note)
    if note is not None:
        if note.strip():
            app.config['ToolInfo'][path + '_note'] = note.strip()
        else:
            app.config['ToolInfo'].pop(path + '_note', None)
        app.config_manager.save_config()
        # 兼容相对 key 或绝对路径
        key = path
        try:
            if hasattr(app, 'storage_path'):
                rel = os.path.relpath(path, app.storage_path)
                if not rel.startswith('..'):
                    key = rel
        except Exception:
            pass

        if key in app.tools_added_record:
            parts = app.config['ToolAddedRecord'].get(key, app.config['ToolAddedRecord'].get(path, '')).split('|', 5)
            if len(parts) == 6:
                parts[4] = note.strip()
                if key in app.config['ToolAddedRecord']:
                    app.config['ToolAddedRecord'][key] = '|'.join(parts)
                else:
                    app.config['ToolAddedRecord'][path] = '|'.join(parts)
                app.config_manager.save_config()
        app.refresh_tools()

def change_tool_icon(app, tool_path, tool_name):
    """更改工具图标"""
    from tkinter import filedialog
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
        messagebox.showinfo("成功", f"图标已更新！\n刷新后生效")
        app.refresh_tools()
    except Exception as e:
        messagebox.showerror("失败", f"图标更换失败: {e}")

def delete_tool(app, path, name):
    """删除工具"""
    if messagebox.askyesno("确认删除", f"确定要删除工具文件吗？\n\n{name}\n\n此操作不可恢复！"):
        try:
            os.remove(path)
            tool_dir = Path(path).parent
            tool_stem = Path(path).stem
            for ext in ['.ico', '.png']:
                custom_icon = tool_dir / f"{tool_stem}{ext}"
                if custom_icon.exists():
                    try:
                        custom_icon.unlink()
                    except Exception as exc:
                        print(f"删除自定义图标失败: {custom_icon} ({exc})")
            app.config['ToolInfo'].pop(path + '_name', None)
            app.config['ToolInfo'].pop(path + '_note', None)
            # 删除 ToolAddedRecord，支持相对 key 或绝对路径
            key = path
            try:
                if hasattr(app, 'storage_path'):
                    rel = os.path.relpath(path, app.storage_path)
                    if not rel.startswith('..'):
                        key = rel
            except Exception:
                pass

            app.config['ToolAddedRecord'].pop(key, None)
            app.config['ToolAddedRecord'].pop(path, None)
            app.config_manager.save_config()
            if key in app.tools_added_record:
                del app.tools_added_record[key]
            elif path in app.tools_added_record:
                del app.tools_added_record[path]
            messagebox.showinfo("成功", f"已删除：{name}")
            app.refresh_tools()
        except Exception as e:
            messagebox.showerror("删除失败", str(e))

def simple_input(root, title, default=""):
    """简单的输入对话框"""
    win = Toplevel(root)
    win.title(title)
    win.geometry("380x180")
    win.transient(root)
    win.grab_set()

    Label(win, text=title, font=("Microsoft YaHei", 11)).pack(pady=20)

    var = StringVar(value=default)
    entry = Entry(win, textvariable=var, width=40, font=("Microsoft YaHei", 11))
    entry.pack(pady=10)
    entry.focus()
    entry.select_range(0, 'end')

    result = [None]
    def ok():
        result[0] = var.get().strip()
        win.destroy()

    Button(win, text="确定", width=10, command=ok).pack(pady=10)
    win.bind("<Return>", lambda e: ok())
    win.wait_window()
    return result[0]

def show_note_editor(root, current_note):
    """显示备注编辑器"""
    from tkinter import Text, Scrollbar as TkScrollbar
    
    win = Toplevel(root)
    win.title("编辑工具备注")
    win.geometry("500x400")
    win.transient(root)
    win.grab_set()

    Label(win, text="工具备注（支持多行）", font=("Microsoft YaHei", 12)).pack(pady=10)

    text_frame = Frame(win)
    text_frame.pack(fill="both", expand=True, padx=20, pady=10)

    text = Text(text_frame, font=("Microsoft YaHei", 11), wrap="word")
    scrollbar = TkScrollbar(text_frame, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    text.insert("1.0", current_note)

    btn_frame = Frame(win)
    btn_frame.pack(pady=10)

    result = [None]
    def save():
        result[0] = text.get("1.0", "end")
        win.destroy()

    Button(btn_frame, text="保存", width=10, bg="#27ae60", fg="white", command=save).pack(side="left", padx=10)
    Button(btn_frame, text="取消", width=10, command=win.destroy).pack(side="left", padx=10)

    win.wait_window()
    return result[0]
