# File: ToolBox/app/ui/tool_panel.py

from tkinter import Label, Frame, Button, Entry, StringVar
from tkinter import ttk

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
    
    # 注意：这里不再调用 show_welcome_message()
    # 因为在 app.py 的 initial_load() 中会自动调用 load_and_display_tools()
    # 如果当前分类为空，会自动显示“暂无工具”的提示