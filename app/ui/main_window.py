# File: ToolBox/app/ui/main_window.py
from tkinter import Label, Frame, Button
import os

def setup_window(root, config):
    root.title("便携软件管理箱")
    try:
        if os.path.exists('icon.ico'):
            root.iconbitmap('icon.ico')
    except Exception as exc:
        print(f"加载窗口图标失败: {exc}")
    root.geometry("1200x800")
    root.minsize(1000, 600)
    root.configure(bg='#f0f0f0')

def create_ui(app):
    from .category_panel import create_category_panel
    from .tool_panel import create_tool_panel
   
    title_frame = Frame(app.root, bg='#2c3e50', height=60)
    title_frame.pack(fill='x')
    title_frame.pack_propagate(False)
   
    Label(title_frame, text="便携软件管理箱", font=("Microsoft YaHei", 16, "bold"),
          fg="white", bg="#2c3e50").pack(side='left', padx=20)
   
    app.auto_status_label = Label(title_frame, text="自动记录: 运行中",
                                  font=("Microsoft YaHei", 10), fg="#1abc9c", bg="#2c3e50")
    app.auto_status_label.pack(side='right', padx=20)
   
    main_frame = Frame(app.root, bg='#f0f0f0')
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    # 赋值给 app 以供其他模块访问和修改
    app.main_frame = main_frame
   
    create_category_panel(app, main_frame)
    create_tool_panel(app, main_frame)
   
    # 状态栏
    status_frame = Frame(app.root, bg='#2c3e50', height=30)
    status_frame.pack(side='bottom', fill='x')
    status_frame.pack_propagate(False)
   
    app.status_label = Label(status_frame, text="就绪", font=("Microsoft YaHei", 9),
                             fg='white', bg='#2c3e50')
    app.status_label.pack(side='left', padx=10)
   
    app.category_status_label = Label(status_frame, text="", font=("Microsoft YaHei", 9),
                                      fg='#ecf0f1', bg='#2c3e50')
    app.category_status_label.pack(side='left', padx=20)
   
    app.tool_count_label = Label(status_frame, text="工具数量: 0", font=("Microsoft YaHei", 9),
                                 fg='#ecf0f1', bg='#2c3e50')
    app.tool_count_label.pack(side='right', padx=10)
