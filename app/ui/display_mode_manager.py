# File: ToolBox/app/ui/display_mode_manager.py

from tkinter import Frame, Label, Radiobutton, StringVar


def add_display_mode_switch(app):
    """添加显示模式切换"""
    parent = app.tools_container.master
    
    switch_frame = Frame(parent, bg='#f0f0f0')
    switch_frame.pack(fill='x', before=app.tools_container, pady=(10, 5))
    
    Label(switch_frame, text="显示模式：", font=("Microsoft YaHei", 10), bg='#f0f0f0').pack(side='left', padx=10)
    
    var_mode = StringVar(value=app.display_mode)
    
    Radiobutton(switch_frame, text="图标模式", variable=var_mode, value='grid',
                font=("Microsoft YaHei", 10), bg='#f0f0f0', command=lambda: switch_display_mode(app)).pack(side='left')
    Radiobutton(switch_frame, text="列表模式", variable=var_mode, value='list',
                font=("Microsoft YaHei", 10), bg='#f0f0f0', command=lambda: switch_display_mode(app)).pack(side='left', padx=10)
    
    app.var_display_mode = var_mode


def switch_display_mode(app):
    """切换显示模式"""
    try:
        new_mode = app.var_display_mode.get()
        print(f"switch_display_mode: 变量值={new_mode}, 当前 app.display_mode={getattr(app,'display_mode',None)}")
        if new_mode != app.display_mode:
            app.display_mode = new_mode
            app.config['General']['display_mode'] = new_mode
            app.config_manager.save_config()
            print(f"switch_display_mode: 已更新 app.display_mode 为 {new_mode}，刷新工具视图")
            app.refresh_tools()
    except Exception as e:
        print(f"switch_display_mode 出现异常: {e}")