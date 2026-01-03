# File: ToolBox/app/app.py

import os
import sys
import time
import threading
import subprocess
import zipfile
import tarfile
from shutil import copyfile
try:
    import rarfile
except ImportError:
    rarfile = None
try:
    import py7zr
except ImportError:
    py7zr = None

# 用于提取 exe 版本号
try:
    import win32api
except ImportError:
    win32api = None

from tkinter import (
    Tk, StringVar, Button, messagebox, Label, Frame, Menu, Canvas,
    Scrollbar, Toplevel, filedialog, Checkbutton, BooleanVar,
    Entry, Text, Scrollbar as TkScrollbar, Radiobutton, Listbox
)
from tkinter import ttk
from pathlib import Path
from datetime import datetime

# Windows 图标提取模块
try:
    import win32ui
    import win32gui
    import win32con
    from win32com.shell import shell, shellcon
except ImportError:
    win32ui = win32gui = win32con = shell = shellcon = None

from .config.config_manager import ConfigManager
from .ui.main_window import setup_window, create_ui
from .services.tool_scanner import load_tools_record, record_tool_usage


class ToolBox:
    def __init__(self):
        self.root = Tk()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        setup_window(self.root, self.config)
        
        self.file_monitor_running = False
        self.last_scan_time = 0
        self.scan_interval = int(self.config['General'].get('scan_interval', '30'))
        self.current_subcategory = ""
        self.current_category = 1
        self.showing_all_tools = False
        self.current_displayed_tools = []

        self.display_mode = self.config['General'].get('display_mode', 'grid')

        # 工具添加记录
        self.tools_added_record = {}
        self.load_tools_added_record()

        load_tools_record(self)
        
        create_ui(self)
        
        self.add_display_mode_switch()
        
        # 自动创建 ToolBox 主文件夹
        toolbox_dir = self.get_app_dir() / "ToolBox"
        toolbox_dir.mkdir(exist_ok=True)
        
        auto_record = self.config['General'].get('auto_record', '1') == '1'
        if auto_record:
            self.start_file_monitor()
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

    def add_display_mode_switch(self):
        parent = self.tools_container.master
        
        switch_frame = Frame(parent, bg='#f0f0f0')
        switch_frame.pack(fill='x', before=self.tools_container, pady=(10, 5))
        
        Label(switch_frame, text="显示模式：", font=("Microsoft YaHei", 10), bg='#f0f0f0').pack(side='left', padx=10)
        
        var_mode = StringVar(value=self.display_mode)
        
        Radiobutton(switch_frame, text="图标模式", variable=var_mode, value='grid',
                    font=("Microsoft YaHei", 10), bg='#f0f0f0', command=self.switch_display_mode).pack(side='left')
        Radiobutton(switch_frame, text="列表模式", variable=var_mode, value='list',
                    font=("Microsoft YaHei", 10), bg='#f0f0f0', command=self.switch_display_mode).pack(side='left', padx=10)
        
        self.var_display_mode = var_mode

    def switch_display_mode(self):
        new_mode = self.var_display_mode.get()
        if new_mode != self.display_mode:
            self.display_mode = new_mode
            self.config['General']['display_mode'] = new_mode
            self.config_manager.save_config()
            self.refresh_tools()

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
• 点击左侧下方的 “分类设置” 按钮管理分类
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

祝您使用愉快！如果需要帮助，可随时查看 “自动记录设置” 或 “分类设置”。

—— 便携软件管理箱 v1.0"""

        frame = Frame(self.tools_container, bg='white')
        frame.pack(fill='both', expand=True)
        
        Label(frame, text=welcome_text,
              font=("Microsoft YaHei", 12), fg='#2c3e50', bg='white',
              justify='left', padx=60, pady=60, wraplength=700).pack(expand=True)

    def start_file_monitor(self):
        if not self.file_monitor_running:
            self.file_monitor_running = True
            self.auto_status_label.config(text="自动记录: 运行中", fg="#1abc9c")
            threading.Thread(target=self.file_monitor_loop, daemon=True).start()

    def file_monitor_loop(self):
        while self.file_monitor_running:
            time.sleep(5)
            try:
                if time.time() - self.last_scan_time >= self.scan_interval:
                    self.last_scan_time = time.time()
                    self.root.after(0, self.refresh_tools)
            except:
                pass

    # ==================== 工具类型与格式化 ====================

    def get_file_type_category(self, ext):
        ext = ext.lower()
        if ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}:
            return "压缩包"
        if ext in {'.exe', '.msi', '.com'}:
            return "可执行文件"
        if ext in {'.bat', '.cmd', '.ps1', '.vbs', '.py', '.sh'}:
            return "脚本文件"
        if ext == '.reg':
            return "注册表"
        if ext == '.lnk':
            return "快捷方式"
        if ext in {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.md', '.html'}:
            return "文档"
        return "其他"

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}".replace('.0', '')
            size /= 1024
        return f"{size:.1f} TB"

    def get_icon_for_filetype(self, file_type, ext):
        icons = {
            '压缩包': '📦', '可执行文件': '⚙️', '脚本文件': '📜',
            '注册表': '🔧', '快捷方式': '🔗', '文档': '📄', '其他': '📎'
        }
        special = {
            '.zip': '🗜️', '.rar': '🗜️', '.7z': '🗜️', '.pdf': '📕',
            '.exe': '⚙️', '.png': '🖼️', '.jpg': '🖼️', '.mp3': '🎵', '.mp4': '🎬'
        }
        return special.get(ext.lower(), icons.get(file_type, '📎'))

    # ==================== 图标提取 ====================

    def get_tool_icon(self, tool_path, tool_name):
        tool_dir = Path(tool_path).parent
        tool_stem = Path(tool_path).stem
        
        custom_ico = tool_dir / f"{tool_stem}.ico"
        custom_png = tool_dir / f"{tool_stem}.png"
        if custom_ico.exists():
            return self.create_icon_photo(custom_ico)
        if custom_png.exists():
            return self.create_icon_photo(custom_png)
        
        if Path(tool_path).suffix.lower() == '.exe':
            icon = self.extract_exe_icon(tool_path)
            if icon:
                return icon
        
        ext = Path(tool_path).suffix.lower()
        file_type = self.get_file_type_category(ext)
        return self.get_icon_for_filetype(file_type, ext)

    def create_icon_photo(self, icon_path):
        if not hasattr(self, 'icon_cache'):
            self.icon_cache = {}
        
        key = str(icon_path)
        if key in self.icon_cache:
            return self.icon_cache[key]
        
        try:
            from PIL import Image, ImageTk
            img = Image.open(icon_path)
            img = img.resize((48, 48), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.icon_cache[key] = photo
            return photo
        except Exception as e:
            print(f"加载自定义图标失败: {e}")
            return None

    def extract_exe_icon(self, exe_path):
        if not all([win32ui, win32gui, shell, shellcon]):
            return None
        
        try:
            from PIL import Image, ImageTk
            
            flags = shellcon.SHGFI_ICON | shellcon.SHGFI_LARGEICON
            shinfo = shell.SHGetFileInfo(exe_path, 0, flags)
            if len(shinfo) >= 4 and shinfo[3] and shinfo[3] != 0:
                hicon = shinfo[3]
                
                hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, 48, 48)
                hdc_mem = hdc.CreateCompatibleDC()
                hdc_mem.SelectObject(hbmp)
                hdc_mem.DrawIcon((0, 0), hicon)
                
                bmp_info = hbmp.GetInfo()
                bmp_str = hbmp.GetBitmapBits(True)
                img = Image.frombuffer('RGBA', (bmp_info['bmWidth'], bmp_info['bmHeight']), bmp_str, 'raw', 'BGRA', 0, 1)
                
                win32gui.DestroyIcon(hicon)
                hdc_mem.DeleteDC()
                hdc.DeleteDC()
                
                photo = ImageTk.PhotoImage(img.resize((48, 48), Image.LANCZOS))
                return photo
        except Exception as e:
            print(f"提取 exe 图标失败: {e}")
        
        return None

    # ==================== 工具添加记录 ====================

    def load_tools_added_record(self):
        """加载工具添加记录"""
        self.tools_added_record = {}
        if 'ToolAddedRecord' in self.config:
            for key in self.config['ToolAddedRecord']:
                value = self.config['ToolAddedRecord'][key]
                try:
                    parts = value.split('|', 5)
                    if len(parts) == 6:
                        name, category, add_time, tool_type, note, version = parts
                        self.tools_added_record[key] = {
                            'name': name,
                            'category': category,
                            'add_time': add_time,
                            'type': tool_type,
                            'note': note,
                            'version': version
                        }
                except:
                    pass

    def record_tool_added(self, tool_path, tool_name, category, note=""):
        """记录工具添加信息"""
        tool_path = str(Path(tool_path))
        if tool_path in self.tools_added_record:
            return
        
        add_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tool_type = self.get_file_type_category(Path(tool_path).suffix)
        
        version = "-"
        if win32api and Path(tool_path).suffix.lower() == '.exe':
            try:
                info = win32api.GetFileVersionInfo(tool_path, "\\")
                ms = info['FileVersionMS']
                ls = info['FileVersionLS']
                version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            except:
                version = "未知"
        
        record_value = f"{tool_name}|{category}|{add_time}|{tool_type}|{note}|{version}"
        self.config['ToolAddedRecord'][tool_path] = record_value
        self.config_manager.save_config()
        
        self.tools_added_record[tool_path] = {
            'name': tool_name,
            'category': category,
            'add_time': add_time,
            'type': tool_type,
            'note': note,
            'version': version
        }

    # ==================== 扫描工具（自动记录添加信息） ====================

    def scan_directory(self, directory: Path, category_name: str):
        tools = []
        supported = {'.exe', '.msi', '.zip', '.rar', '.7z', '.pdf', '.txt', '.bat', '.cmd',
                     '.reg', '.lnk', '.png', '.jpg', '.mp4', '.mp3', '.py', '.docx', '.xlsx', '.pptx'}
        if not directory.exists():
            return tools
        try:
            for p in directory.iterdir():
                if p.is_file() and p.suffix.lower() in supported:
                    st = p.stat()
                    tool_path = str(p)
                    custom_name = self.config.get('ToolInfo', tool_path + '_name', fallback=p.stem)
                    note = self.config.get('ToolInfo', tool_path + '_note', fallback='')
                    tools.append({
                        'name': custom_name,
                        'path': tool_path,
                        'ext': p.suffix.lower(),
                        'type': self.get_file_type_category(p.suffix),
                        'size': self.format_size(st.st_size),
                        'category': category_name,
                        'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d'),
                        'note': note
                    })
                    self.record_tool_added(tool_path, custom_name, category_name, note)
        except Exception as e:
            print(f"扫描目录 {directory} 时出错: {e}")
        return sorted(tools, key=lambda x: x['name'].lower())

    def scan_directory_for_archives(self, directory: Path, category_name: str):
        archives = []
        exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}
        if not directory.exists():
            return archives
        try:
            for p in directory.iterdir():
                if p.is_file() and p.suffix.lower() in exts:
                    st = p.stat()
                    archives.append({
                        'name': p.stem,
                        'path': str(p),
                        'ext': p.suffix.lower(),
                        'size': self.format_size(st.st_size),
                        'category': category_name
                    })
                    self.record_tool_added(str(p), p.stem, category_name)
        except:
            pass
        return archives

    # ==================== 显示工具 ====================

    def get_current_scan_info(self):
        if self.showing_all_tools:
            return Path(self.get_app_dir() / "ToolBox"), "所有工具", True
        
        cat_name = self.config['Categories'].get(str(self.current_category), f"分类{self.current_category}")
        base = Path(self.get_app_dir() / "ToolBox") / cat_name
        
        if self.current_subcategory:
            return base / self.current_subcategory, f"{cat_name} - {self.current_subcategory}", False
        return base, cat_name, False

    def load_and_display_tools(self):
        dir_path, display_name, is_all = self.get_current_scan_info()
        
        if is_all:
            self.load_and_display_all_tools()
            return
        
        tools = self.scan_directory(dir_path, display_name)
        
        search_text = self.search_var.get().lower()
        if search_text:
            tools = [t for t in tools if search_text in t['name'].lower() or search_text in t['ext']]
        
        type_filter = self.filetype_var.get()
        if type_filter != "全部":
            tools = [t for t in tools if t['type'] == type_filter]
        
        self.current_displayed_tools = tools
        self.display_tools_grid(tools, display_name, len(tools))

    def load_and_display_all_tools(self):
        all_tools = []
        base = Path(self.get_app_dir() / "ToolBox")
        if base.exists():
            for cat_dir in base.iterdir():
                if cat_dir.is_dir():
                    cat_name = cat_dir.name
                    all_tools.extend(self.scan_directory(cat_dir, cat_name))
                    for sub_dir in cat_dir.iterdir():
                        if sub_dir.is_dir():
                            all_tools.extend(self.scan_directory(sub_dir, f"{cat_name} - {sub_dir.name}"))
        
        search_text = self.search_var.get().lower()
        if search_text:
            all_tools = [t for t in all_tools if search_text in t['name'].lower()]
        if self.filetype_var.get() != "全部":
            all_tools = [t for t in all_tools if t['type'] == self.filetype_var.get()]
        
        self.current_displayed_tools = all_tools
        self.display_tools_grid(all_tools, "所有工具", len(all_tools))

    def display_tools_grid(self, tools, category_name, count):
        for widget in self.tools_container.winfo_children():
            widget.destroy()
        
        if len(tools) == 0:
            if int(self.config['Categories'].get('count', '0')) == 0:
                self.show_welcome_page()
            else:
                Label(self.tools_container,
                      text="此分类下暂无工具文件\n\n请将便携程序放入对应文件夹",
                      font=("Microsoft YaHei", 14), fg="#95a5a6", bg='white').pack(expand=True, pady=100)
            self.category_status_label.config(text=f"分类: {category_name}")
            self.tool_count_label.config(text=f"工具数量: {count}")
            return
        
        if self.display_mode == 'grid':
            self.display_grid_mode(tools, category_name, count)
        else:
            self.display_list_mode(tools, category_name, count)

    def display_grid_mode(self, tools, category_name, count):
        canvas = Canvas(self.tools_container, bg='white', highlightthickness=0)
        scrollbar = Scrollbar(self.tools_container, orient="vertical", command=canvas.yview)
        frame = Frame(canvas, bg='white')
        
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        cols = 5
        for i, tool in enumerate(tools):
            r, c = divmod(i, cols)
            item_frame = Frame(frame, bg="#f8f9fa", relief="raised", bd=1, padx=10, pady=10)
            item_frame.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            
            icon_photo = self.get_tool_icon(tool['path'], tool['name'])
            if icon_photo and hasattr(icon_photo, 'width'):
                icon_label = Label(item_frame, image=icon_photo, bg="#f8f9fa")
                icon_label.image = icon_photo
            else:
                icon_label = Label(item_frame, text=icon_photo or self.get_icon_for_filetype(tool['type'], tool['ext']),
                                   font=("Segoe UI Emoji", 36), bg="#f8f9fa")
            icon_label.pack()
            
            name_label = Label(item_frame, text=tool['name'], font=("Microsoft YaHei", 9, "bold"),
                               bg="#f8f9fa", wraplength=120, justify="center")
            name_label.pack(pady=(4,1))
            
            info_label = Label(item_frame, text=f"{tool['ext'].upper()} • {tool['size']}",
                               font=("Microsoft YaHei", 7), fg="#7f8c8d", bg="#f8f9fa")
            info_label.pack()
            
            if tool.get('note'):
                note_label = Label(item_frame, text=tool['note'], font=("Microsoft YaHei", 7), fg="#7f8c8d",
                                   bg="#f8f9fa", wraplength=120, justify="center")
                note_label.pack(pady=(1,0))
            
            item_frame.bind("<Double-Button-1>", lambda e, p=tool['path']: self.run_tool(p))
            item_frame.bind("<Enter>", lambda e, f=item_frame: f.config(bg="#e8f4fd"))
            item_frame.bind("<Leave>", lambda e, f=item_frame: f.config(bg="#f8f9fa"))
            
            widgets_to_bind = [item_frame, icon_label, name_label, info_label]
            if tool.get('note'):
                widgets_to_bind.append(note_label)
            
            for widget in widgets_to_bind:
                self.add_context_menu(widget, tool)
        
        for i in range(cols):
            frame.grid_columnconfigure(i, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.category_status_label.config(text=f"分类: {category_name}")
        self.tool_count_label.config(text=f"工具数量: {count}")

    def display_list_mode(self, tools, category_name, count):
        tree_frame = Frame(self.tools_container)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("no", "icon", "name", "ext", "size", "mtime", "note")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        tree.heading("no", text="序号")
        tree.heading("icon", text="")
        tree.heading("name", text="名称")
        tree.heading("ext", text="类型")
        tree.heading("size", text="大小")
        tree.heading("mtime", text="添加时间")
        tree.heading("note", text="备注")
        
        tree.column("no", width=60, anchor="center")
        tree.column("icon", width=50, anchor="center")
        tree.column("name", width=280, anchor="w")
        tree.column("ext", width=80, anchor="center")
        tree.column("size", width=100, anchor="center")
        tree.column("mtime", width=120, anchor="center")
        tree.column("note", width=280, anchor="w")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for idx, tool in enumerate(tools, start=1):
            icon_photo = self.get_tool_icon(tool['path'], tool['name'])
            if icon_photo and hasattr(icon_photo, 'width'):
                tree.insert("", "end", values=(idx, "", tool['name'], tool['ext'].upper(), tool['size'], tool['mtime'], tool.get('note', '')),
                            image=icon_photo)
            else:
                tree.insert("", "end", values=(idx, "", tool['name'], tool['ext'].upper(), tool['size'], tool['mtime'], tool.get('note', '')),
                            text=icon_photo or self.get_icon_for_filetype(tool['type'], tool['ext']))
        
        tree.bind("<Double-Button-1>", lambda e: self.run_tool_from_tree(tree))
        tree.bind("<Button-3>", lambda e: self.show_tool_context_menu(e, tree, tools))
        
        self.category_status_label.config(text=f"分类: {category_name}")
        self.tool_count_label.config(text=f"工具数量: {count}")

    def run_tool_from_tree(self, tree):
        item = tree.selection()
        if item:
            index = tree.index(item[0])
            if 0 <= index < len(self.current_displayed_tools):
                path = self.current_displayed_tools[index]['path']
                self.run_tool(path)

    def show_tool_context_menu(self, event, tree, tools):
        item = tree.identify_row(event.y)
        if item:
            index = tree.index(item)
            if 0 <= index < len(tools):
                tool = tools[index]
                menu = Menu(self.root, tearoff=0)
                menu.add_command(label="运行工具", command=lambda: self.run_tool(tool['path']))
                menu.add_command(label="打开所在文件夹", command=lambda: self.open_folder(tool['path']))
                menu.add_command(label="复制文件路径", command=lambda: self.copy_path(tool['path']))
                menu.add_separator()
                menu.add_command(label="修改工具标题", command=lambda: self.rename_tool(tool['path'], tool['name']))
                menu.add_command(label="添加/编辑备注", command=lambda: self.edit_note(tool['path']))
                menu.add_command(label="修改图标", command=lambda: self.change_tool_icon(tool['path'], tool['name']))
                menu.add_separator()
                menu.add_command(label="删除此工具文件", command=lambda: self.delete_tool(tool['path'], tool['name']+tool['ext']))
                menu.add_separator()
                menu.add_command(label="刷新当前分类", command=self.refresh_tools)
                
                try:
                    menu.tk_popup(event.x_root, event.y_root)
                finally:
                    menu.grab_release()

    def add_context_menu(self, widget, tool):
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="运行工具", command=lambda: self.run_tool(tool['path']))
        menu.add_command(label="打开所在文件夹", command=lambda: self.open_folder(tool['path']))
        menu.add_command(label="复制文件路径", command=lambda: self.copy_path(tool['path']))
        menu.add_separator()
        menu.add_command(label="修改工具标题", command=lambda: self.rename_tool(tool['path'], tool['name']))
        menu.add_command(label="添加/编辑备注", command=lambda: self.edit_note(tool['path']))
        menu.add_command(label="修改图标", command=lambda: self.change_tool_icon(tool['path'], tool['name']))
        menu.add_separator()
        menu.add_command(label="删除此工具文件", command=lambda: self.delete_tool(tool['path'], tool['name']+tool['ext']))
        menu.add_separator()
        menu.add_command(label="刷新当前分类", command=self.refresh_tools)
        
        def show_menu(e):
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()
        
        widget.bind("<Button-3>", show_menu)

    def change_tool_icon(self, tool_path, tool_name):
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
                except:
                    pass
        
        ext = Path(icon_path).suffix.lower()
        target_path = tool_dir / f"{tool_stem}{ext}"
        try:
            copyfile(icon_path, target_path)
            messagebox.showinfo("成功", f"图标已更新！\n刷新后生效")
            self.refresh_tools()
        except Exception as e:
            messagebox.showerror("失败", f"图标更换失败: {e}")

    def run_tool(self, path):
        if os.path.exists(path):
            try:
                subprocess.Popen(path, shell=True)
                for tool in self.current_displayed_tools:
                    if tool['path'] == path:
                        record_tool_usage(self, tool['path'], tool['name'] + tool['ext'], tool['category'])
                        break
            except Exception as e:
                messagebox.showerror("运行失败", str(e))
        else:
            messagebox.showerror("错误", "文件不存在")

    def open_folder(self, path):
        folder = os.path.dirname(path)
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showerror("错误", "文件夹不存在")

    def copy_path(self, path):
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.root.update()
        messagebox.showinfo("成功", f"文件路径已复制：\n{path}")

    def rename_tool(self, path, current_name):
        new_name = simple_input("修改工具标题", current_name)
        if new_name and new_name != current_name:
            self.config['ToolInfo'][path + '_name'] = new_name
            self.config_manager.save_config()
            if path in self.tools_added_record:
                self.tools_added_record[path]['name'] = new_name
                self.config['ToolAddedRecord'][path] = self.config['ToolAddedRecord'][path].replace(current_name, new_name, 1)
                self.config_manager.save_config()
            messagebox.showinfo("成功", f"工具标题已修改为：{new_name}")
            self.refresh_tools()

    def edit_note(self, path):
        current_note = self.config['ToolInfo'].get(path + '_note', '')
        note = self.show_note_editor(current_note)
        if note is not None:
            if note.strip():
                self.config['ToolInfo'][path + '_note'] = note.strip()
            else:
                self.config['ToolInfo'].pop(path + '_note', None)
            self.config_manager.save_config()
            if path in self.tools_added_record:
                parts = self.config['ToolAddedRecord'][path].split('|', 5)
                parts[4] = note.strip()
                self.config['ToolAddedRecord'][path] = '|'.join(parts)
                self.config_manager.save_config()
            self.refresh_tools()

    def show_note_editor(self, current_note):
        win = Toplevel(self.root)
        win.title("编辑工具备注")
        win.geometry("500x400")
        win.transient(self.root)
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

    def delete_tool(self, path, name):
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
                        except:
                            pass
                self.config['ToolInfo'].pop(path + '_name', None)
                self.config['ToolInfo'].pop(path + '_note', None)
                self.config['ToolAddedRecord'].pop(path, None)
                self.config_manager.save_config()
                if path in self.tools_added_record:
                    del self.tools_added_record[path]
                messagebox.showinfo("成功", f"已删除：{name}")
                self.refresh_tools()
            except Exception as e:
                messagebox.showerror("删除失败", str(e))

    # ==================== 树状分类导航 ====================

    def refresh_category_tree(self):
        from .ui.category_panel import refresh_category_tree
        refresh_category_tree(self)

    def get_subcategories_for_category(self, cat_id):
        subs = []
        try:
            name = self.config['Categories'].get(str(cat_id), f"分类{cat_id}")
            cat_dir = self.get_app_dir() / "ToolBox" / name
            if cat_dir.exists() and cat_dir.is_dir():
                for d in cat_dir.iterdir():
                    if d.is_dir():
                        subs.append(d.name)
        except Exception as e:
            print(f"读取二级分类失败: {e}")
        return sorted(subs)

    def on_tree_select(self, event):
        tree = self.category_tree
        selected = tree.selection()
        if not selected:
            return
        
        item = selected[0]
        text = tree.item(item, "text").strip()
        
        parent = tree.parent(item)
        if parent == "":  # 一级分类
            children = tree.get_children("")
            for idx, child in enumerate(children, 1):
                if child == item:
                    self.current_category = idx
                    self.current_subcategory = ""
                    self.showing_all_tools = False
                    self.load_and_display_tools()
                    tree.item(item, open=True)
                    break
        else:  # 二级分类
            parent_idx = None
            main_children = tree.get_children("")
            for idx, child in enumerate(main_children, 1):
                if child == parent:
                    parent_idx = idx
                    break
            if parent_idx:
                sub_name = text[2:].strip()
                self.current_category = parent_idx
                self.current_subcategory = sub_name
                self.showing_all_tools = False
                self.load_and_display_tools()

    def on_tree_double_click(self, event):
        tree = self.category_tree
        item = tree.identify_row(event.y)
        if item:
            current = tree.item(item, "open")
            tree.item(item, open=not current)

    def select_category(self, category_id):
        self.current_category = category_id
        self.current_subcategory = ""
        self.showing_all_tools = False
        
        tree = self.category_tree
        children = tree.get_children("")
        if 1 <= category_id <= len(children):
            node = children[category_id - 1]
            tree.selection_set(node)
            tree.item(node, open=True)
        
        self.load_and_display_tools()

    def show_all_tools(self):
        self.showing_all_tools = True
        self.current_category = 0
        self.current_subcategory = ""
        self.category_tree.selection_remove(self.category_tree.selection())
        self.load_and_display_all_tools()

    def search_tools(self):
        self.load_and_display_tools()

    def filter_by_type(self, event=None):
        self.load_and_display_tools()

    def refresh_tools(self):
        self.load_and_display_tools()

    def scan_for_new_tools(self):
        self.refresh_tools()

    def extract_selected_archive(self):
        messagebox.showinfo("提示", "请在“压缩包管理”中双击压缩包进行解压")

    # ==================== 分类设置（支持软件内创建/删除二级分类） ====================

    def show_category_settings(self):
        win = Toplevel(self.root)
        win.title("分类设置")
        win.geometry("800x500")
        win.resizable(False, False)
        win.configure(bg='#f0f0f0')
        win.transient(self.root)
        win.grab_set()

        Label(win, text="分类管理", font=("Microsoft YaHei", 18, "bold"), bg='#f0f0f0', fg='#2c3e50').pack(pady=20)

        paned = ttk.PanedWindow(win, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=20, pady=10)

        left_frame = Frame(paned, bg='#f0f0f0')
        paned.add(left_frame, weight=1)

        Label(left_frame, text="一级分类", font=("Microsoft YaHei", 12), bg='#f0f0f0').pack(pady=5)

        left_list_frame = Frame(left_frame, bg='#f0f0f0')
        left_list_frame.pack(fill='both', expand=True)

        left_listbox = Listbox(left_list_frame, font=("Microsoft YaHei", 11), height=10)
        left_scrollbar = Scrollbar(left_list_frame, command=left_listbox.yview)
        left_listbox.configure(yscrollcommand=left_scrollbar.set)
        left_listbox.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

        count = int(self.config['Categories'].get('count', '0'))
        for i in range(1, count + 1):
            name = self.config['Categories'].get(str(i), f"分类{i}")
            left_listbox.insert('end', name)

        left_input_frame = Frame(left_frame, bg='#f0f0f0')
        left_input_frame.pack(pady=10)

        Label(left_input_frame, text="一级分类名称：", font=("Microsoft YaHei", 11), bg='#f0f0f0').grid(row=0, column=0, padx=5)
        var_primary = StringVar()
        entry_primary = Entry(left_input_frame, textvariable=var_primary, width=20, font=("Microsoft YaHei", 11))
        entry_primary.grid(row=0, column=1, padx=5)

        def add_primary():
            name = var_primary.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入一级分类名称")
                return
            if name in [left_listbox.get(i) for i in range(left_listbox.size())]:
                messagebox.showwarning("提示", "该一级分类已存在")
                return
            
            count = int(self.config['Categories'].get('count', '0')) + 1
            self.config['Categories']['count'] = str(count)
            self.config['Categories'][str(count)] = name
            
            folder = self.get_app_dir() / "ToolBox" / name
            folder.mkdir(exist_ok=True)
            
            self.config_manager.save_config()
            left_listbox.insert('end', name)
            var_primary.set("")
            messagebox.showinfo("成功", f"一级分类 '{name}' 添加成功！")
            self.refresh_category_tree()
            self.refresh_tools()

        def delete_primary():
            selection = left_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个一级分类")
                return
            name = left_listbox.get(selection[0])
            if messagebox.askyesno("确认删除", f"确定要删除一级分类 '{name}' 吗？\n\n文件夹和工具不会被删除，仅从列表移除"):
                count = int(self.config['Categories'].get('count', '0'))
                for i in range(1, count + 1):
                    if self.config['Categories'].get(str(i)) == name:
                        for j in range(i, count):
                            self.config['Categories'][str(j)] = self.config['Categories'].get(str(j+1), '')
                        self.config['Categories'].pop(str(count), None)
                        self.config['Categories']['count'] = str(count - 1)
                        break
                self.config_manager.save_config()
                left_listbox.delete(selection[0])
                right_listbox.delete(0, 'end')
                messagebox.showinfo("成功", f"一级分类 '{name}' 已删除")
                self.refresh_category_tree()
                self.refresh_tools()

        Button(left_input_frame, text="添加一级分类", font=("Microsoft YaHei", 11), width=15, bg="#27ae60", fg="white", command=add_primary).grid(row=1, column=0, pady=10, padx=5)
        Button(left_input_frame, text="删除选中一级分类", font=("Microsoft YaHei", 11), width=18, bg="#e74c3c", fg="white", command=delete_primary).grid(row=1, column=1, pady=10, padx=5)

        right_frame = Frame(paned, bg='#f0f0f0')
        paned.add(right_frame, weight=1)

        Label(right_frame, text="二级分类（选中一级分类后显示）", font=("Microsoft YaHei", 12), bg='#f0f0f0').pack(pady=5)

        right_list_frame = Frame(right_frame, bg='#f0f0f0')
        right_list_frame.pack(fill='both', expand=True)

        right_listbox = Listbox(right_list_frame, font=("Microsoft YaHei", 11), height=10)
        right_scrollbar = Scrollbar(right_list_frame, command=right_listbox.yview)
        right_listbox.configure(yscrollcommand=right_scrollbar.set)
        right_listbox.pack(side="left", fill="both", expand=True)
        right_scrollbar.pack(side="right", fill="y")

        right_input_frame = Frame(right_frame, bg='#f0f0f0')
        right_input_frame.pack(pady=10)

        Label(right_input_frame, text="二级分类名称：", font=("Microsoft YaHei", 11), bg='#f0f0f0').grid(row=0, column=0, padx=5)
        var_secondary = StringVar()
        entry_secondary = Entry(right_input_frame, textvariable=var_secondary, width=20, font=("Microsoft YaHei", 11))
        entry_secondary.grid(row=0, column=1, padx=5)

        def load_secondary(event=None):
            selection = left_listbox.curselection()
            if not selection:
                right_listbox.delete(0, 'end')
                return
            index = selection[0] + 1
            subs = self.get_subcategories_for_category(index)
            right_listbox.delete(0, 'end')
            for sub in subs:
                right_listbox.insert('end', sub)

        left_listbox.bind("<<ListboxSelect>>", load_secondary)

        def add_secondary():
            selection = left_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个一级分类")
                return
            name = var_secondary.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入二级分类名称")
                return
            if name in [right_listbox.get(i) for i in range(right_listbox.size())]:
                messagebox.showwarning("提示", "该二级分类已存在")
                return
            
            primary_name = left_listbox.get(selection[0])
            sub_folder = self.get_app_dir() / "ToolBox" / primary_name / name
            sub_folder.mkdir(exist_ok=True)
            
            right_listbox.insert('end', name)
            var_secondary.set("")
            messagebox.showinfo("成功", f"二级分类 '{name}' 添加成功！")
            self.refresh_category_tree()
            self.refresh_tools()

        def delete_secondary():
            selection = right_listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个二级分类")
                return
            name = right_listbox.get(selection[0])
            primary_selection = left_listbox.curselection()
            if not primary_selection:
                return
            primary_name = left_listbox.get(primary_selection[0])
            sub_folder = self.get_app_dir() / "ToolBox" / primary_name / name
            
            if messagebox.askyesno("确认删除", f"确定要删除二级分类 '{name}' 吗？\n\n文件夹和工具不会被删除，仅从列表移除"):
                if sub_folder.exists():
                    try:
                        sub_folder.rmdir()
                    except:
                        pass
                right_listbox.delete(selection[0])
                messagebox.showinfo("成功", f"二级分类 '{name}' 已删除")
                self.refresh_category_tree()
                self.refresh_tools()

        Button(right_input_frame, text="添加二级分类", font=("Microsoft YaHei", 11), width=15, bg="#27ae60", fg="white", command=add_secondary).grid(row=1, column=0, pady=10, padx=5)
        Button(right_input_frame, text="删除选中二级分类", font=("Microsoft YaHei", 11), width=18, bg="#e74c3c", fg="white", command=delete_secondary).grid(row=1, column=1, pady=10, padx=5)

        Button(win, text="关闭", font=("Microsoft YaHei", 11), width=10, bg="#95a5a6", fg="white", command=win.destroy).pack(pady=10)

    # ==================== 工具添加记录 ====================

    def show_tools_added_record(self):
        record_window = Toplevel(self.root)
        record_window.title("工具添加记录")
        record_window.geometry("1200x650")
        record_window.resizable(True, True)
        
        Label(record_window, text="工具添加记录", font=("Microsoft YaHei", 16, "bold"), pady=15).pack()
        
        columns = ("名称", "分类", "路径", "添加时间", "说明", "备注", "版本号")
        tree = ttk.Treeview(record_window, columns=columns, show="headings", height=25)
        
        tree.heading("名称", text="名称")
        tree.heading("分类", text="分类")
        tree.heading("路径", text="路径")
        tree.heading("添加时间", text="添加时间")
        tree.heading("说明", text="说明")
        tree.heading("备注", text="备注")
        tree.heading("版本号", text="版本号")
        
        tree.column("名称", width=180, anchor="w")
        tree.column("分类", width=120, anchor="w")
        tree.column("路径", width=400, anchor="w")
        tree.column("添加时间", width=150, anchor="center")
        tree.column("说明", width=100, anchor="center")
        tree.column("备注", width=150, anchor="w")
        tree.column("版本号", width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(record_window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True, padx=10, pady=(0,10))
        scrollbar.pack(side="right", fill="y", pady=(0,10))
        
        if not self.tools_added_record:
            tree.insert("", "end", values=("暂无添加记录", "", "", "", "", "", ""))
        else:
            sorted_items = sorted(self.tools_added_record.items(),
                                  key=lambda x: x[1]['add_time'],
                                  reverse=True)
            for path, rec in sorted_items:
                tree.insert("", "end", values=(
                    rec.get('name', "未知"),
                    rec.get('category', "未知"),
                    path,
                    rec.get('add_time', "-"),
                    rec.get('type', "-"),
                    rec.get('note', ""),
                    rec.get('version', "-")
                ))
        
        def on_double_click(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item, "values")
            path = values[2]
            if os.path.exists(path):
                self.run_tool(path)
            else:
                messagebox.showwarning("提示", "文件路径已失效，无法运行")
        
        tree.bind("<Double-Button-1>", on_double_click)
        
        record_window.transient(self.root)
        record_window.grab_set()

    # ==================== 兼容旧调用（防止 category_panel.py 报错） ====================

    def show_tools_record(self):
        """兼容旧版本 category_panel.py 中的调用"""
        self.show_tools_added_record()

    # ==================== 其余功能 ====================

    def show_auto_record_settings(self):
        settings_window = Toplevel(self.root)
        settings_window.title("自动记录设置")
        settings_window.geometry("520x520")
        settings_window.resizable(False, False)
        settings_window.configure(bg='#f0f0f0')
        settings_window.transient(self.root)
        settings_window.grab_set()

        title_label = Label(settings_window, text="自动记录设置", font=("Microsoft YaHei", 18, "bold"),
                            bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=25)

        content_frame = Frame(settings_window, bg='#f0f0f0')
        content_frame.pack(padx=40, pady=10, fill="both", expand=True)

        auto_record = self.config['General'].get('auto_record', '1') == '1'
        scan_interval = self.config['General'].get('scan_interval', '30')
        notify_new = self.config['General'].get('notify_new_tools', '1') == '1'
        auto_create = self.config['General'].get('auto_create_folders', '1') == '1'
        show_welcome = self.config['General'].get('show_welcome_on_startup', '1') == '1'

        var_auto = BooleanVar(value=auto_record)
        Checkbutton(content_frame, text="启用自动记录新工具", variable=var_auto,
                    font=("Microsoft YaHei", 11), bg='#f0f0f0', selectcolor='#ffffff').pack(anchor="w", pady=12)

        interval_frame = Frame(content_frame, bg='#f0f0f0')
        interval_frame.pack(anchor="w", pady=8)
        Label(interval_frame, text="扫描间隔（秒）：", font=("Microsoft YaHei", 11), bg='#f0f0f0').pack(side="left")
        var_interval = StringVar(value=scan_interval)
        entry_interval = ttk.Entry(interval_frame, textvariable=var_interval, width=10, font=("Microsoft YaHei", 11))
        entry_interval.pack(side="left", padx=10)
        Label(interval_frame, text="(最小 10 秒)", font=("Microsoft YaHei", 9), fg="#7f8c8d", bg='#f0f0f0').pack(side="left")

        var_notify = BooleanVar(value=notify_new)
        Checkbutton(content_frame, text="发现新工具时弹出通知", variable=var_notify,
                    font=("Microsoft YaHei", 11), bg='#f0f0f0', selectcolor='#ffffff').pack(anchor="w", pady=12)

        var_create = BooleanVar(value=auto_create)
        Checkbutton(content_frame, text="自动创建缺失的分类文件夹", variable=var_create,
                    font=("Microsoft YaHei", 11), bg='#f0f0f0', selectcolor='#ffffff').pack(anchor="w", pady=12)

        var_welcome = BooleanVar(value=show_welcome)
        Checkbutton(content_frame, text="每次启动显示欢迎页面", variable=var_welcome,
                    font=("Microsoft YaHei", 11), bg='#f0f0f0', selectcolor='#ffffff').pack(anchor="w", pady=12)

        btn_frame = Frame(settings_window, bg='#f0f0f0')
        btn_frame.pack(pady=30)

        def save_settings():
            try:
                new_interval = int(var_interval.get().strip())
                if new_interval < 10:
                    messagebox.showwarning("提示", "扫描间隔不能小于10秒")
                    return
            except ValueError:
                messagebox.showerror("错误", "扫描间隔必须是数字")
                return

            self.config['General']['auto_record'] = '1' if var_auto.get() else '0'
            self.config['General']['scan_interval'] = str(new_interval)
            self.config['General']['notify_new_tools'] = '1' if var_notify.get() else '0'
            self.config['General']['auto_create_folders'] = '1' if var_create.get() else '0'
            self.config['General']['show_welcome_on_startup'] = '1' if var_welcome.get() else '0'
            self.config_manager.save_config()

            self.scan_interval = new_interval
            if var_auto.get():
                if not self.file_monitor_running:
                    self.start_file_monitor()
            else:
                self.file_monitor_running = False
                self.auto_status_label.config(text="自动记录: 已停止", fg="#e74c3c")

            messagebox.showinfo("成功", "设置已保存并立即生效！")
            settings_window.destroy()

        Button(btn_frame, text="保存设置", font=("Microsoft YaHei", 11), width=15, bg="#27ae60", fg="white",
               command=save_settings).pack(side="left", padx=15)
        Button(btn_frame, text="取消", font=("Microsoft YaHei", 11), width=15, bg="#95a5a6", fg="white",
               command=settings_window.destroy).pack(side="left", padx=15)

    def show_archive_manager(self):
        all_archives = []
        base = Path(self.get_app_dir() / "ToolBox")
        if base.exists():
            for cat_dir in base.iterdir():
                if cat_dir.is_dir():
                    cat_name = cat_dir.name
                    all_archives.extend(self.scan_directory_for_archives(cat_dir, cat_name))
                    for sub_dir in cat_dir.iterdir():
                        if sub_dir.is_dir():
                            all_archives.extend(self.scan_directory_for_archives(sub_dir, f"{cat_name} - {sub_dir.name}"))

        archive_window = Toplevel(self.root)
        archive_window.title("压缩包管理")
        archive_window.geometry("950x650")
        archive_window.transient(self.root)
        archive_window.grab_set()

        Label(archive_window, text="压缩包管理", font=("Microsoft YaHei", 16, "bold"), pady=15).pack()

        columns = ("文件名", "分类", "路径", "大小", "格式")
        tree = ttk.Treeview(archive_window, columns=columns, show="headings", height=22)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=160, anchor="w")
        tree.column("文件名", width=220)
        tree.column("路径", width=350)

        scrollbar = ttk.Scrollbar(archive_window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0,10), pady=10)

        if not all_archives:
            tree.insert("", "end", values=("暂无压缩包文件", "", "", "", ""))
        else:
            for archive in sorted(all_archives, key=lambda x: x['name'].lower()):
                tree.insert("", "end", values=(
                    archive['name'] + archive['ext'],
                    archive['category'],
                    archive['path'],
                    archive['size'],
                    archive['ext'].upper()
                ))

        def on_double_click(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item, "values")
            path = values[2]
            if os.path.exists(path):
                self.extract_archive(path)
            else:
                messagebox.showwarning("提示", "文件不存在")

        tree.bind("<Double-Button-1>", on_double_click)

        btn_frame = Frame(archive_window)
        btn_frame.pack(pady=15)
        Button(btn_frame, text="刷新", command=lambda: [archive_window.destroy(), self.show_archive_manager()]).pack(side="left", padx=10)
        Button(btn_frame, text="关闭", command=archive_window.destroy).pack(side="left", padx=10)

    def extract_archive(self, path):
        extract_to = filedialog.askdirectory(title="选择解压目录")
        if not extract_to:
            return
        
        ext = Path(path).suffix.lower()
        try:
            if ext == '.zip':
                with zipfile.ZipFile(path, 'r') as zf:
                    zf.extractall(extract_to)
            elif ext == '.rar' and rarfile:
                with rarfile.RarFile(path, 'r') as rf:
                    rf.extractall(extract_to)
            elif ext == '.7z' and py7zr:
                with py7zr.SevenZipFile(path, 'r') as szf:
                    szf.extractall(extract_to)
            else:
                with tarfile.open(path, 'r:*') as tf:
                    tf.extractall(extract_to)
            
            messagebox.showinfo("成功", f"解压完成到：\n{extract_to}")
            self.refresh_tools()
        except Exception as e:
            messagebox.showerror("解压失败", str(e))

def simple_input(title, default=""):
    win = Toplevel()
    win.title(title)
    win.geometry("380x180")
    win.transient()
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