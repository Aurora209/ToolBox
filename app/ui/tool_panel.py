# File: ToolBox/app/ui/tool_panel.py

from tkinter import Label, Frame, Button, Entry, StringVar
from tkinter import ttk
import os
import shutil
from pathlib import Path

def create_tool_panel(app, parent):
    """创建右侧工具面板"""
    tool_frame = Frame(parent, bg='white', relief='sunken', bd=1)
    tool_frame.pack(side='left', fill='both', expand=True)
    
    # 工具栏
    toolbar = Frame(tool_frame, bg='#ecf0f1', height=40)
    toolbar.pack(fill='x')
    toolbar.pack_propagate(False)
    
    # 搜索框
    search_frame = Frame(toolbar, bg='#ecf0f1')
    search_frame.pack(side='left', padx=10, pady=5)
    
    Label(search_frame, text="搜索:", bg='#ecf0f1', font=("Microsoft YaHei", 10)).pack(side='left')
    
    app.search_var = StringVar()
    # 搜索内容改变时自动触发
    app.search_var.trace("w", lambda *args: app.load_and_display_tools())
    search_entry = Entry(search_frame, textvariable=app.search_var,
                         width=30, font=("Microsoft YaHei", 10))
    search_entry.pack(side='left', padx=5)
    
    # 类型筛选
    type_frame = Frame(toolbar, bg='#ecf0f1')
    type_frame.pack(side='left', padx=10, pady=5)
    
    Label(type_frame, text="类型:", bg='#ecf0f1', font=("Microsoft YaHei", 10)).pack(side='left')
    
    app.filetype_var = StringVar(value="全部")
    filetype_combo = ttk.Combobox(type_frame, textvariable=app.filetype_var,
                                  values=["全部", "可执行文件", "脚本文件", "注册表",
                                          "快捷方式", "压缩包", "文档", "其他"],
                                  width=15, state="readonly")
    filetype_combo.pack(side='left')
    filetype_combo.bind("<<ComboboxSelected>>", app.filter_by_type)
    
    # 新增：拖放行为配置（复制 / 移动）
    action_frame = Frame(toolbar, bg='#ecf0f1')
    action_frame.pack(side='left', padx=10, pady=5)
    Label(action_frame, text="拖放操作:", bg='#ecf0f1', font=("Microsoft YaHei", 10)).pack(side='left')
    
    # 默认使用 '复制'，允许用户选择 '复制' 或 '移动'
    if not hasattr(app, 'drag_action'):
        # 初始化时优先读取 app.settings 或环境变量（见 get_drag_action）
        app.drag_action = get_drag_action(app)
    app.drag_action_var = StringVar(value=("移动" if app.drag_action == 'move' else "复制"))
    action_combo = ttk.Combobox(action_frame, textvariable=app.drag_action_var,
                                values=["复制", "移动"], width=10, state="readonly")
    action_combo.pack(side='left')
    def _on_action_change(event):
        val = app.drag_action_var.get()
        app.drag_action = 'move' if val == '移动' else 'copy'
    action_combo.bind("<<ComboboxSelected>>", _on_action_change)
    
    # 按钮组
    Button(toolbar, text="搜索", font=("Microsoft YaHei", 10),
           bg='#27ae60', fg='white', command=app.search_tools).pack(side='left', padx=5)
    
    Button(toolbar, text="刷新", font=("Microsoft YaHei", 10),
           bg='#e67e22', fg='white', command=app.refresh_tools).pack(side='left', padx=5)
    
    Button(toolbar, text="扫描新工具", font=("Microsoft YaHei", 10),
           bg='#3498db', fg='white', command=app.scan_for_new_tools).pack(side='left', padx=5)
    
    Button(toolbar, text="解压选中", font=("Microsoft YaHei", 10),
           bg='#9b59b6', fg='white', command=app.extract_selected_archive).pack(side='left', padx=5)
    
    # 工具显示容器
    app.tools_container = Frame(tool_frame, bg='white')
    app.tools_container.pack(fill='both', expand=True, padx=10, pady=10)
    # 将按钮栏暴露给 app（用于在切换显示模式时保留）
    app.button_frame = toolbar
    
    # 启用拖放功能
    setup_drag_drop(app.tools_container, app)
    
    # 注意：这里不再调用 show_welcome_message()
    # 因为在 app.py 的 initial_load() 中会自动调用 load_and_display_tools()
    # 如果当前分类为空，会自动显示"暂无工具"的提示

def setup_drag_drop(container, app):
    """设置拖放功能"""
    # 优先使用 windnd（Windows），更稳定地获取外部拖入的文件路径
    try:
        import windnd

        def _on_drop(files):
            # windnd 回调返回 bytes 列表
            paths = []
            for f in files:
                try:
                    if isinstance(f, (bytes, bytearray, memoryview)):
                        p = f.decode('utf-8')
                    else:
                        p = str(f)
                    paths.append(p)
                except Exception:
                    continue
            process_dropped_paths(paths, app)

        windnd.hook_dropfiles(container, _on_drop)
        container.config(bg='#e8f4fd')  # 轻微改变背景色以显示支持拖放
        return
    except Exception:
        pass

    # 回退到 tkinter.dnd（如果可用）
    try:
        import tkinter.dnd as dnd
        if hasattr(container, 'drop_target_register'):
            try:
                container.drop_target_register(dnd.DND_FILES)
                container.dnd_bind('<<Drop>>', lambda e: handle_drop(e, app))
                container.config(bg='#e8f4fd')
                return
            except Exception:
                pass
    except Exception:
        pass

    # 无风格拖放库时，使用 enter/leave 作为视觉提示，并保留剪贴板模拟
    def on_drag_enter(event):
        container.config(bg='#d6eaf8')

    def on_drag_leave(event):
        container.config(bg='white')

    container.bind("<Enter>", on_drag_enter)
    container.bind("<Leave>", on_drag_leave)
    container.config(bg='#e8f4fd')

# 新增：统一处理由不同途径得到的路径列表
def process_dropped_paths(paths, app):
    """处理拖放得到的若干路径（字符串列表）"""
    try:
        from tkinter import messagebox
        # 获取当前分类信息
        dir_path, display_name, is_all = app.get_current_scan_info()
        if is_all:
            messagebox.showwarning("警告", "请先选择一个分类，再拖放文件")
            return

        target_dir = Path(dir_path)
        for p in paths:
            if not p:
                continue
            move_file_to_category(p, target_dir, app)
        app.refresh_tools()
    except Exception as e:
        print(f"处理拖入路径失败: {e}")

def handle_drop_win32(event, app):
    """兼容的 Windows 拖放处理入口（保留接口）"""
    try:
        # 如果被调用时传入的是路径列表，直接处理
        if isinstance(event, (list, tuple)):
            process_dropped_paths(list(event), app)
            return
        # 其他情况尽量忽略（真实的 win32 处理交给 windnd）
    except Exception as e:
        print(f"handle_drop_win32 失败: {e}")

def handle_drop(event, app):
    """处理 tkinter.dnd 的拖放事件（event.data）"""
    try:
        from tkinter import messagebox
        # 获取当前分类信息
        dir_path, display_name, is_all = app.get_current_scan_info()
        if is_all:
            messagebox.showwarning("警告", "请先选择一个分类，再拖放文件")
            return

        # event.data 可能是以空格分隔的路径，使用 tk 的 splitlist 安全拆分
        files = app.root.tk.splitlist(event.data)
        process_dropped_paths(files, app)
    except Exception as e:
        print(f"处理拖放事件失败: {e}")

# 新增：统一读取拖放操作配置
def get_drag_action(app):
    """返回 'copy' 或 'move'，优先级：app.drag_action -> app.settings['drag_action'] -> 环境变量 -> 默认 'copy'"""
    try:
        # 1) 已在 app 上直接设置
        if hasattr(app, 'drag_action') and app.drag_action in ('copy', 'move'):
            return app.drag_action
        # 2) 检查 app.settings 或 app.config
        if hasattr(app, 'settings') and isinstance(app.settings, dict):
            v = app.settings.get('drag_action')
            if v in ('copy', 'move'):
                return v
        if hasattr(app, 'config') and isinstance(app.config, dict):
            v = app.config.get('drag_action')
            if v in ('copy', 'move'):
                return v
        # 3) 环境变量
        import os
        env = os.getenv('TOOLBOX_DRAG_ACTION', '').lower()
        if env in ('copy', 'move'):
            return env
    except Exception:
        pass
    # 默认值
    return 'copy'

# 修改：将移动改为复制，处理文件/目录并做重名检测
def move_file_to_category(file_path, target_dir, app):
    """将文件或文件夹复制/移动到指定分类目录（行为由配置决定）"""
    try:
        source_path = Path(file_path)
        if not source_path.exists():
            return False

        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / source_path.name

        # 处理同名文件，添加后缀 _1,_2...
        counter = 1
        original_target = target_path
        while target_path.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_path = original_target.parent / f"{stem}_{counter}{suffix}"
            counter += 1

        # 根据配置决定是复制还是移动
        action = get_drag_action(app) if not hasattr(app, 'drag_action') else app.drag_action
        if action == 'move':
            # 执行移动（会删除原始文件/文件夹）
            if source_path.is_file() or source_path.is_dir():
                shutil.move(str(source_path), str(target_path))
            else:
                return False
        else:
            # 默认复制（保留原文件）
            if source_path.is_file():
                shutil.copy2(str(source_path), str(target_path))
            elif source_path.is_dir():
                shutil.copytree(str(source_path), str(target_path))
            else:
                return False

        # 记录工具添加信息（保持原实现）
        from ..services.tool_scanner import record_tool_added
        category_name = target_dir.name
        record_tool_added(app, str(target_path), target_path.stem, category_name)

        return True
    except Exception as e:
        from tkinter import messagebox
        msg = "移动文件失败" if (hasattr(app, 'drag_action') and app.drag_action == 'move') else "复制文件失败"
        messagebox.showerror("错误", f"{msg}: {e}")
        return False