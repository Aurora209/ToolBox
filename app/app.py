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
from .ui.display_mode_manager import add_display_mode_switch
from .services.tool_scanner import (
    load_tools_record,
    record_tool_usage,
    scan_directory,
    scan_directory_for_archives,
    record_tool_added as _record_tool_added,
)
from .services.file_monitor import FileMonitor
from .utils.file_utils import get_file_version_info
from .utils.icon_utils import get_tool_icon as _get_tool_icon  # ✅ 新增：绑定图标方法
from .utils.icon_utils import get_file_type_category
from .services.category_service import (
    get_current_scan_info, get_subcategories_for_category,
    load_and_display_tools, load_and_display_all_tools
)
from .services.display_service import display_tools_grid


class ToolBox:
    def __init__(self):
        self.root = Tk()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        setup_window(self.root, self.config)

        # 确保 ToolAddedRecord 分区存在
        try:
            if 'ToolAddedRecord' not in self.config:
                self.config['ToolAddedRecord'] = {}
                self.config_manager.save_config()
        except Exception as exc:
            print(f"初始化 ToolAddedRecord 分区失败: {exc}")

        # UI 创建前初始化 Storage 路径
        toolbox_dir = self.get_app_dir() / "Storage"
        toolbox_dir.mkdir(exist_ok=True)
        self.storage_path = str(toolbox_dir)

        # ✅ 图标缓存 + 绑定 get_tool_icon
        self.icon_cache = {}
        self.get_tool_icon = lambda tool_path, tool_name, size=48: _get_tool_icon(self, tool_path, tool_name, size=size)

        # 初始化文件监控
        self.file_monitor = FileMonitor(self)

        self.current_subcategory = ""
        self.current_category = 1
        self.showing_all_tools = False
        self.current_displayed_tools = []

        self.display_mode = self.config['General'].get('display_mode', 'grid')

        # 工具添加记录（依赖 storage_path）
        self.tools_added_record = {}
        self.load_tools_added_record()

        load_tools_record(self)

        # UI 相关属性占位
        self.tree = None
        self.main_frame = None
        self.category_tree = None
        self.tools_container = None

        create_ui(self)
        add_display_mode_switch(self)

        # 绑定文件版本读取函数
        try:
            self.get_file_version_info = get_file_version_info
        except Exception as exc:
            print(f"绑定文件版本函数失败: {exc}")

        auto_record = self.config['General'].get('auto_record', '1') == '1'
        if auto_record:
            self.file_monitor.start()
        else:
            try:
                self.auto_status_label.config(text="自动记录: 已停止", fg="#e74c3c")
            except Exception:
                pass

        self.root.after(300, self.check_show_welcome)
        self.root.mainloop()

    def get_app_dir(self):
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent

    def check_show_welcome(self):
        show_welcome = self.config['General'].get('show_welcome_on_startup', '1') == '1'
        total_categories = int(self.config['Categories'].get('count', '0'))
        if show_welcome or total_categories == 0:
            self.show_welcome_page()

    def get_file_type_category(self, ext):
        return get_file_type_category(ext)

    def load_tools_added_record(self):
        self.tools_added_record = {}
        if 'ToolAddedRecord' in self.config:
            for key in self.config['ToolAddedRecord']:
                value = self.config['ToolAddedRecord'][key]
                try:
                    parts = value.split('|', 5)
                    if len(parts) >= 6:
                        self.tools_added_record[key] = {
                            'name': parts[0],
                            'category': parts[1],
                            'add_time': parts[2],
                            'type': parts[3],
                            'note': parts[4],
                            'version': parts[5]
                        }
                except Exception:
                    pass

    def record_tool_added(self, tool_path, tool_name, category, note=""):
        return _record_tool_added(self, tool_path, tool_name, category, note)

    def show_tools_added_record(self):
        from .services.tool_record_service import show_tools_added_record
        show_tools_added_record(self)

    def show_tools_record(self):
        self.show_tools_added_record()

    def show_auto_record_settings(self):
        from .ui.dialogs import show_auto_record_settings
        show_auto_record_settings(self)

    def show_archive_manager(self):
        from .ui.archive_manager import show_archive_manager
        show_archive_manager(self)

    def show_category_settings(self):
        from .ui.dialogs import show_category_settings
        show_category_settings(self)

    def add_context_menu(self, widget, tool):
        from .ui.context_menu import add_context_menu
        add_context_menu(self, widget, tool)

    def show_tool_context_menu(self, event, tree, tools):
        from .ui.context_menu import show_tool_context_menu
        show_tool_context_menu(self, event, tree, tools)

    def load_and_display_tools(self):
        if not hasattr(self, '_waiting_for_init'):
            self._waiting_for_init = False
        if not self._waiting_for_init:
            self._waiting_for_init = True
            self._delayed_load_and_display_tools(max_retries=10)

    def _delayed_load_and_display_tools(self, max_retries=10, current_retry=0):
        if self.tree is None:
            if current_retry < max_retries:
                self.root.after(200, lambda: self._delayed_load_and_display_tools(max_retries, current_retry + 1))
            else:
                self._waiting_for_init = False
            return

        self._waiting_for_init = False

        if getattr(self, "showing_all_tools", False):
            self.load_and_display_all_tools()
            return

        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            if item.get('values') and len(item['values']) > 0 and item['values'][0]:
                load_and_display_tools(self, item['values'][0])
                return

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

    def refresh_tools(self):
        if getattr(self, 'showing_all_tools', False):
            self.load_and_display_all_tools()
        else:
            self.load_and_display_tools()

    def search_tools(self):
        self.refresh_tools()

    def filter_by_type(self, event=None):
        self.refresh_tools()

    def scan_for_new_tools(self):
        self.refresh_tools()

    def extract_selected_archive(self):
        messagebox.showinfo("提示", "请在\"压缩包管理\"中双击压缩包进行解压")

    def refresh_category_tree(self):
        from .ui.category_panel import refresh_category_tree
        refresh_category_tree(self)

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

    def get_current_scan_info(self):
        return get_current_scan_info(self)

    def get_subcategories_for_category(self, cat_id):
        return get_subcategories_for_category(self, cat_id)

    def scan_directory(self, directory: Path, category_name: str):
        return scan_directory(self, directory, category_name)

    def scan_directory_for_archives(self, directory: Path, category_name: str):
        return scan_directory_for_archives(self, directory, category_name)

    def show_welcome_page(self):
        from .ui.welcome_page import show_welcome_page
        show_welcome_page(self)
