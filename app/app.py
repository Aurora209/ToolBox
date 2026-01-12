# File: ToolBox/app/app.py

import os
import sys
import threading
import time
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Entry, Button, StringVar, BooleanVar, Radiobutton,
    messagebox
)
from tkinter import ttk

from .config.config_manager import ConfigManager
from .services.tool_scanner import (
    load_tools_record,
    scan_directory,
    scan_directory_for_archives,
    record_tool_added,
    record_tool_usage
)
from .services.display_service import display_tools_grid
from .services.archive_service import extract_archive
from .services.file_monitor import FileMonitor
from .services.category_service import (
    load_and_display_tools,
    load_and_display_all_tools,
    get_subcategories_for_category,
    get_current_scan_info
)
from .ui.main_window import setup_window, create_ui
from .ui.category_panel import refresh_category_tree
from .ui.display_mode_manager import add_display_mode_switch
from .ui.display_manager import display_list_mode, display_grid_mode
from .utils.icon_utils import get_file_icon
from .utils.file_utils import open_folder_location
from .utils.tool_manager import run_tool, delete_tool, copy_path, open_folder
from .utils.type_utils import get_file_type_category
from .utils.file_utils import get_file_version_info


class ToolBox:
    def __init__(self):
        self.root = Tk()

        # 配置
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        # 状态变量
        self.search_var = StringVar()
        self.filetype_var = StringVar()
        self.display_mode_var = StringVar()
        self.auto_record_var = BooleanVar()
        self.copy_mode_var = StringVar()

        # 当前选择状态
        self.current_category = None
        self.current_category_name = "所有工具"
        self.current_tools = []
        self.current_displayed_tools = []
        self.selected_category_path = None
        self.selected_category_depth = 0
        self.showing_all_tools = True

        # 显示模式
        self.display_mode = self.config.get('General', 'display_mode', fallback='grid')
        self.display_mode_var.set(self.display_mode)

        # 自动记录
        auto_record = self.config.get('General', 'auto_record', fallback='1')
        self.auto_record_var.set(auto_record == '1')

        # 拖拽操作模式
        copy_mode = self.config.get('General', 'copy_mode', fallback='复制')
        self.copy_mode_var.set(copy_mode)

        # UI
        setup_window(self.root, self.config)
        create_ui(self)

        # 显示模式切换
        add_display_mode_switch(self)

        # ✅ 强制以“程序/项目目录下的 Storage”作为唯一根目录（不依赖 cwd/盘符）
        toolbox_dir = (self.get_app_dir() / "Storage").resolve()
        toolbox_dir.mkdir(parents=True, exist_ok=True)

        # ✅ 统一为绝对路径；后续扫描/记录/清理都应以该目录为根
        self.storage_path = os.path.abspath(str(toolbox_dir))

        # 将文件版本读取函数绑定为 app 的方法，便于其它模块调用
        try:
            self.get_file_version_info = get_file_version_info
        except Exception as exc:
            print(f"绑定文件版本函数失败: {exc}")

        # 初始化工具使用记录
        try:
            load_tools_record(self)
        except Exception as exc:
            print(f"加载tools_record失败: {exc}")

        # 加载工具添加记录
        try:
            self.load_tools_added_record()
        except Exception as exc:
            print(f"加载工具添加记录失败: {exc}")

        # 文件监控
        self.file_monitor = FileMonitor(self)

        # 刷新分类树
        refresh_category_tree(self)

        # 绑定事件
        self.bind_events()

        # 欢迎页
        self.root.after(300, self.check_show_welcome)

        self.root.mainloop()

    def get_app_dir(self):
        """获取程序所在目录（支持打包后的 exe）；开发态返回项目根目录 ToolBox/"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent  # ToolBox 根目录

    # ==================== 欢迎页 ====================

    def check_show_welcome(self):
        try:
            show_welcome = self.config.get('General', 'show_welcome_on_startup', fallback='1') == '1'
            total_categories = int(self.config.get('Categories', 'count', fallback='0'))
            if show_welcome or total_categories == 0:
                self.show_welcome_page()
        except Exception:
            pass

    def show_welcome_page(self):
        try:
            for widget in self.tools_container.winfo_children():
                widget.destroy()
        except Exception:
            return

        welcome_text = """欢迎使用便携软件管理箱！

【快速开始】
1. 左侧创建/选择分类
2. 将软件文件拖拽到右侧工具面板（支持复制/移动）
3. 右键工具可运行/打开目录/复制路径/删除等
4. 顶部可切换图标模式/列表模式
"""
        label = Label(self.tools_container, text=welcome_text, justify="left", anchor="nw")
        label.pack(fill="both", expand=True, padx=20, pady=20)

    # ==================== 事件绑定 ====================

    def bind_events(self):
        try:
            from .ui.category_manager import on_tree_select
            tree = getattr(self, "category_tree", None) or getattr(self, "tree", None)
            if tree is not None:
                tree.bind("<<TreeviewSelect>>", lambda e: on_tree_select(self, e))
        except Exception as e:
            print(f"绑定分类树事件失败: {e}")

        try:
            if hasattr(self, "search_entry") and self.search_entry is not None:
                self.search_entry.bind("<Return>", lambda e: self.search_tools())
        except Exception:
            pass

    # ==================== 分类/显示 ====================

    def load_and_display_tools(self, selected_path=None):
        if not selected_path:
            selected_path = self.selected_category_path or self.storage_path
        load_and_display_tools(self, selected_path)

    def load_and_display_all_tools(self):
        load_and_display_all_tools(self)

    def display_tools_grid(self, tools, category_name, count):
        display_tools_grid(self, tools, category_name, count)

    def refresh_tools(self):
        self.load_and_display_tools()

    def search_tools(self):
        self.load_and_display_tools()

    def filter_by_type(self, event=None):
        self.load_and_display_tools()

    # ==================== 压缩包处理 ====================

    def extract_selected_archive(self):
        messagebox.showinfo("提示", "请在“压缩包管理”中双击压缩包进行解压")

    # ==================== 分类设置（支持软件内创建/删除二级分类） ====================

    def show_category_settings(self):
        from .ui.dialogs import show_category_settings
        show_category_settings(self)

    # ==================== 工具添加记录 ====================

    def show_tools_added_record(self):
        from .services.tool_record_service import show_tools_added_record
        show_tools_added_record(self)

    # ==================== 兼容旧调用（防止其它文件报错） ====================

    def show_tools_record(self):
        self.show_tools_added_record()

    def show_all_tools(self):
        from .ui.category_manager import show_all_tools
        show_all_tools(self)

    def show_archive_manager(self):
        from .ui.archive_manager import show_archive_manager
        show_archive_manager(self)

    def show_auto_record_settings(self):
        from .ui.dialogs import show_auto_record_settings
        show_auto_record_settings(self)

    # ==================== ToolAddedRecord 加载 ====================

    def load_tools_added_record(self):
        """
        加载 ToolAddedRecord（版本/添加时间/备注等）。
        key 统一规范化为相对 storage_path 的路径 + lower。
        """
        self.tools_added_record = {}
        if 'ToolAddedRecord' not in self.config:
            return

        sec = self.config['ToolAddedRecord']
        for key in sec:
            try:
                value = sec.get(key, "")
                if not value:
                    continue

                # key 规范化
                normalized_key = key
                if os.path.isabs(key):
                    try:
                        rel = os.path.relpath(key, self.storage_path)
                        if not rel.startswith(".."):
                            normalized_key = rel
                    except Exception:
                        normalized_key = key

                normalized_key = normalized_key.replace("/", "\\").strip().lower()

                parts = value.split("|")
                # name|category|add_time|type|note|version
                tool_name = parts[0] if len(parts) > 0 else ""
                category = parts[1] if len(parts) > 1 else ""
                add_time = parts[2] if len(parts) > 2 else ""
                tool_type = parts[3] if len(parts) > 3 else ""
                note = parts[4] if len(parts) > 4 else ""
                version = parts[5] if len(parts) > 5 else ""

                self.tools_added_record[normalized_key] = {
                    "name": tool_name,
                    "category": category,
                    "add_time": add_time,
                    "type": tool_type,
                    "note": note,
                    "version": version
                }
            except Exception:
                continue
