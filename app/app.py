# File: ToolBox/app/app.py

import os
import sys
import time
import threading
import subprocess
from tkinter import (
    Tk, StringVar, Button, messagebox, Label, Frame, Menu, Canvas,
    Scrollbar, Toplevel, filedialog, Checkbutton, BooleanVar,
    Entry, Text, Scrollbar as TkScrollbar, Radiobutton, Listbox
)
from tkinter import ttk
from pathlib import Path
from datetime import datetime

from .config.config_manager import ConfigManager
from .ui.main_window import setup_window, create_ui
from .services.tool_scanner import (
    load_tools_record, record_tool_usage, scan_directory, 
    scan_directory_for_archives, record_tool_added
)
from .services.file_monitor import FileMonitor
from .utils.file_utils import get_file_version_info
from .utils.icon_utils import get_file_type_category
from .services.archive_service import extract_archive
from .utils.tool_manager import (
    run_tool, open_folder, copy_path, rename_tool, edit_note, 
    change_tool_icon, delete_tool, simple_input, show_note_editor
)
from .services.category_service import (
    get_current_scan_info, get_subcategories_for_category, 
    load_and_display_tools, load_and_display_all_tools
)
from .services.display_service import display_tools_grid
from .ui.display_mode_manager import add_display_mode_switch, switch_display_mode


class ToolBox:
    def __init__(self):
        self.root = Tk()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        setup_window(self.root, self.config)
        
        # 初始化文件监控
        self.file_monitor = FileMonitor(self)
        
        self.current_subcategory = ""
        self.current_category = 1
        self.showing_all_tools = False
        self.current_displayed_tools = []

        self.display_mode = self.config['General'].get('display_mode', 'grid')

        # 工具添加记录
        self.tools_added_record = {}
        self.load_tools_added_record()  # 调用方法加载记录

        load_tools_record(self)
        
        # 初始化tree属性为None，稍后在create_ui中设置
        self.tree = None
        # 添加main_frame属性初始化
        self.main_frame = None
        # 添加category_tree属性初始化
        self.category_tree = None
        # 添加tools_container属性初始化
        self.tools_container = None
        
        create_ui(self)
        
        # 确保tree在UI创建后被正确设置
        if hasattr(self, 'tree_frame') and hasattr(self, 'tree'):
            pass  # tree已经在create_ui中设置好了
        
        add_display_mode_switch(self)
        
        # 修改：自动创建 Storage 主文件夹在应用目录下
        toolbox_dir = self.get_app_dir() / "Storage"
        toolbox_dir.mkdir(exist_ok=True)
        
        # 添加：初始化 storage_path 属性
        self.storage_path = str(toolbox_dir)  # 转为字符串以兼容 os.path 操作

        # 将文件版本读取函数绑定为 app 的方法，便于其它模块调用
        try:
            self.get_file_version_info = get_file_version_info
        except Exception as exc:
            print(f"绑定文件版本函数失败: {exc}")

        # 重新加载 tools_added_record（确保 keys 能使用 storage_path 规范化）
        try:
            self.load_tools_added_record()
        except Exception as exc:
            print(f"加载工具记录失败: {exc}")

        # 初始化后立即刷新分类树，确保 UI 与磁盘/配置同步
        try:
            self.refresh_category_tree()
            # 如果存在分类，默认选择第一个
            if int(self.config['Categories'].get('count', '0')) > 0:
                self.select_category(1)
        except Exception as exc:
            print(f"初始化分类树失败: {exc}")
        
        auto_record = self.config['General'].get('auto_record', '1') == '1'
        if auto_record:
            self.file_monitor.start()
        else:
            self.auto_status_label.config(text="自动记录: 已停止", fg="#e74c3c")
        
        self.root.after(300, self.check_show_welcome)

        self.root.mainloop()

    def get_app_dir(self):
        """获取程序所在目录（支持打包后的 exe）"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent.parent

    def check_show_welcome(self):
        show_welcome = self.config['General'].get('show_welcome_on_startup', '1') == '1'
        total_categories = int(self.config['Categories'].get('count', '0'))
        
        if show_welcome or total_categories == 0:
            self.show_welcome_page()

    def show_welcome_page(self):
        for widget in self.tools_container.winfo_children():
            widget.destroy()
        
        welcome_text = """欢迎使用便携软件管理箱！

🎉 感谢您选择本工具箱，这是一个专为便携软件设计的轻量级管理器。

【快速开始指南】
• 点击左侧下方的 "分类设置" 按钮管理分类
• 支持一级分类和二级分类（在设置中直接添加）
• 将便携程序放入对应文件夹，即可在此处双击运行

【核心功能】
✓ 树状分类导航（支持一级展开二级）
✓ 双击工具直接运行（显示真实图标）
✓ 支持自定义工具图标（右键 → 修改图标）
✓ 支持图标模式与列表模式切换
✓ 列表模式显示序号与添加时间
✓ 自动记录工具添加信息（含版本号）
✓ 压缩包管理（双击解压）
✓ 全局搜索与类型过滤
✓ 右键菜单支持修改标题、添加备注、修改图标

祝您使用愉快！如果需要帮助，可随时查看 "自动记录设置" 或 "分类设置"。

—— 便携软件管理箱 v1.0"""

        frame = Frame(self.tools_container, bg='white')
        frame.pack(fill='both', expand=True)
        
        Label(frame, text=welcome_text,
              font=("Microsoft YaHei", 12), fg='#2c3e50', bg='white',
              justify='left', padx=60, pady=60, wraplength=700).pack(expand=True)

    # ==================== 工具类型与格式化 ====================

    def get_file_type_category(self, ext):
        return get_file_type_category(ext)

    # ==================== 图标提取 ====================

    def get_tool_icon(self, tool_path, tool_name, size=48):
        from .utils.icon_utils import get_tool_icon
        return get_tool_icon(self, tool_path, tool_name, size=size)

    def create_icon_photo(self, icon_path, size=48):
        from .utils.icon_utils import create_icon_photo
        return create_icon_photo(self, icon_path, size=size)

    def extract_main_icon(self, exe_path, size=48):
        # 兼容性别名（调用现有的 extract_exe_icon 实现）
        from .utils.icon_utils import extract_exe_icon
        return extract_exe_icon(self, exe_path, size=size)

    # ==================== 工具添加记录 ====================

    def load_tools_added_record(self):
        """加载工具添加记录。将配置中保存的 key 规范化为相对于 storage_path 的路径（便于跨设备与移动）。"""
        self.tools_added_record = {}
        if 'ToolAddedRecord' in self.config:
            for key in self.config['ToolAddedRecord']:
                value = self.config['ToolAddedRecord'][key]
                try:
                    # 规范化 key：如果是绝对路径且位于 storage_path 下，转换为相对路径
                    normalized_key = key
                    try:
                        if os.path.isabs(key) and hasattr(self, 'storage_path'):
                            rel = os.path.relpath(key, self.storage_path)
                            # 若rel包含上级路径标识（../），则保留原 key
                            if not rel.startswith('..'):
                                normalized_key = rel
                    except Exception as exc:
                        print(f"规范化工具记录路径失败: {exc}")

                    parts = value.split('|', 5)
                    if len(parts) == 6:
                        name, category, add_time, tool_type, note, version = parts
                        self.tools_added_record[normalized_key] = {
                            'name': name,
                            'category': category,
                            'add_time': add_time,
                            'type': tool_type,
                            'note': note,
                            'version': version
                        }
                except Exception:
                    pass

    def record_tool_added(self, tool_path, tool_name, category, note=""):
        record_tool_added(self, tool_path, tool_name, category, note)

    # ==================== 扫描工具（自动记录添加信息） ====================

    def scan_directory(self, directory: Path, category_name: str):
        return scan_directory(self, directory, category_name)

    def scan_directory_for_archives(self, directory: Path, category_name: str):
        return scan_directory_for_archives(self, directory, category_name)

    # ==================== 显示工具 ====================

    def get_current_scan_info(self):
        return get_current_scan_info(self)

    def load_and_display_tools(self):
        # 检查是否已经在等待初始化，避免重复调用
        if not hasattr(self, '_waiting_for_init'):
            self._waiting_for_init = False
        
        if not self._waiting_for_init:
            self._waiting_for_init = True
            self._delayed_load_and_display_tools(max_retries=10)

    def _delayed_load_and_display_tools(self, max_retries=10, current_retry=0):
        # 确保tree控件已初始化
        if self.tree is None:
            if current_retry < max_retries:
                print(f"Tree控件尚未初始化，使用默认路径 (尝试 {current_retry + 1}/{max_retries})")
                # 延迟再次检查，同时检查是否已经有其他调用在等待
                if not hasattr(self, '_already_waiting'):
                    self._already_waiting = True
                    self.root.after(200, lambda: self._delayed_load_and_display_tools(max_retries, current_retry + 1))
                else:
                    print("已经有加载任务在等待，跳过重复任务")
            else:
                print("错误：Tree控件初始化超时，无法加载工具列表")
                # 重置等待状态，允许后续尝试
                if hasattr(self, '_already_waiting'):
                    delattr(self, '_already_waiting')
                if hasattr(self, '_waiting_for_init'):
                    self._waiting_for_init = False
            return
        
        # 重置等待状态
        self._already_waiting = False
        self._waiting_for_init = False
        
        # 获取当前选中的分类路径
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            if item['values'] and len(item['values']) > 0:  # 确保有值且至少有一个元素
                selected_category_path = item['values'][0]  # 从tree控件获取路径
                load_and_display_tools(self, selected_category_path)
            else:
                # 如果没有值，可能是根目录，使用storage_path
                load_and_display_tools(self, self.storage_path)
        else:
            # 如果没有选择任何分类，显示根目录内容
            load_and_display_tools(self, self.storage_path)

    def load_and_display_all_tools(self):
        load_and_display_all_tools(self)

    def display_tools_grid(self, tools, category_name, count):
        display_tools_grid(self, tools, category_name, count)

    def display_grid_mode(self, tools, category_name, count):
        from .ui.display_manager import display_grid_mode
        display_grid_mode(self, tools, category_name, count)

    def display_list_mode(self, tools, category_name, count):
        from .ui.display_manager import display_list_mode
        display_list_mode(self, tools, category_name, count)

    def run_tool_from_tree(self, tree):
        item = tree.selection()
        if item:
            index = tree.index(item[0])
            if 0 <= index < len(self.current_displayed_tools):
                path = self.current_displayed_tools[index]['path']
                run_tool(self, path)

    def show_tool_context_menu(self, event, tree, tools):
        from .ui.context_menu import show_tool_context_menu
        show_tool_context_menu(self, event, tree, tools)

    def add_context_menu(self, widget, tool):
        from .ui.context_menu import add_context_menu
        add_context_menu(self, widget, tool)

    # ==================== 树状分类导航 ====================

    def refresh_category_tree(self):
        from .ui.category_panel import refresh_category_tree
        refresh_category_tree(self)

    def get_subcategories_for_category(self, cat_id):
        return get_subcategories_for_category(self, cat_id)

    def on_tree_select(self, event):
        from .ui.category_manager import on_tree_select
        on_tree_select(self, event)

    def on_tree_double_click(self, event):
        from .ui.category_manager import on_tree_double_click
        on_tree_double_click(self, event)

    def select_category(self, category_id):
        from .ui.category_manager import select_category
        select_category(self, category_id)

    def show_all_tools(self):
        from .ui.category_manager import show_all_tools
        show_all_tools(self)

    def search_tools(self):
        self.load_and_display_tools()

    def filter_by_type(self, event=None):
        self.load_and_display_tools()

    def refresh_tools(self):
        self.load_and_display_tools()

    def scan_for_new_tools(self):
        self.refresh_tools()

    def extract_selected_archive(self):
        messagebox.showinfo("提示", "请在\"压缩包管理\"中双击压缩包进行解压")

    # ==================== 分类设置（支持软件内创建/删除二级分类） ====================

    def show_category_settings(self):
        from .ui.dialogs import show_category_settings
        show_category_settings(self)

    # ==================== 工具添加记录 ====================

    def show_tools_added_record(self):
        from .services.tool_record_service import show_tools_added_record
        show_tools_added_record(self)

    # ==================== 兼容旧调用（防止 category_panel.py 报错） ====================

    def show_tools_record(self):
        """兼容旧版本 category_panel.py 中的调用"""
        self.show_tools_added_record()

    # ==================== 其余功能 ====================

    def show_auto_record_settings(self):
        from .ui.dialogs import show_auto_record_settings
        show_auto_record_settings(self)

    def show_archive_manager(self):
        from .ui.archive_manager import show_archive_manager
        show_archive_manager(self)
