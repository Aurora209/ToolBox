# File: ToolBox/app/ui/context_menu.py
import tkinter as tk
from tkinter import messagebox

from ..utils.tool_manager import run_tool, open_folder, copy_path, rename_tool, edit_note, change_tool_icon, delete_tool


def add_context_menu(app, widget, tool):
    """为指定 widget 添加右键上下文菜单（用于右侧工具项）"""
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="运行", command=lambda: run_tool(app, tool['path']))
    menu.add_command(label="打开所在文件夹", command=lambda: open_folder(tool['path']))
    menu.add_command(label="复制路径", command=lambda: copy_path(app.root, tool['path']))
    menu.add_separator()
    menu.add_command(label="修改标题", command=lambda: rename_tool(app, tool['path'], tool.get('name', '')))
    menu.add_command(label="编辑备注", command=lambda: edit_note(app, tool['path']))
    menu.add_command(label="修改图标", command=lambda: change_tool_icon(app, tool['path'], tool.get('name', '')))
    menu.add_separator()
    menu.add_command(label="删除", command=lambda: delete_tool(app, tool['path'], tool.get('name','')))

    def on_right_click(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", on_right_click)


def show_tool_context_menu(app, event, tree, tools):
    """在 Treeview 上显示工具的右键菜单（根据选中的项来定位工具）"""
    sel = tree.selection()
    if not sel:
        return
    idx = tree.index(sel[0])
    if idx < 0 or idx >= len(tools):
        return
    tool = tools[idx]

    # 创建并弹出菜单
    menu = tk.Menu(tree, tearoff=0)
    menu.add_command(label="运行", command=lambda: run_tool(app, tool['path']))
    menu.add_command(label="打开所在文件夹", command=lambda: open_folder(tool['path']))
    menu.add_command(label="复制路径", command=lambda: copy_path(app.root, tool['path']))
    menu.add_separator()
    menu.add_command(label="修改标题", command=lambda: rename_tool(app, tool['path'], tool.get('name', '')))
    menu.add_command(label="编辑备注", command=lambda: edit_note(app, tool['path']))
    menu.add_command(label="修改图标", command=lambda: change_tool_icon(app, tool['path'], tool.get('name', '')))
    menu.add_separator()
    menu.add_command(label="删除", command=lambda: delete_tool(app, tool['path'], tool.get('name','')))

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
