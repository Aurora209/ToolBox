# File: ToolBox/app/services/display_service.py

def display_tools_grid(app, tools, category_name, count):
    """显示工具列表或网格"""
    for widget in app.tools_container.winfo_children():
        widget.destroy()
    
    if len(tools) == 0:
        if int(app.config['Categories'].get('count', '0')) == 0:
            app.show_welcome_page()
        else:
            from tkinter import Label
            Label(app.tools_container,
                  text="此分类下暂无工具文件\n\n请将便携程序放入对应文件夹",
                  font=("Microsoft YaHei", 14), fg="#95a5a6", bg='white').pack(expand=True, pady=100)
        app.category_status_label.config(text=f"分类: {category_name}")
        app.tool_count_label.config(text=f"工具数量: {count}")
        return
    
    if app.display_mode == 'grid':
        display_grid_mode(app, tools, category_name, count)
    else:
        display_list_mode(app, tools, category_name, count)


def display_grid_mode(app, tools, category_name, count):
    from .ui.display_manager import display_grid_mode
    display_grid_mode(app, tools, category_name, count)


def display_list_mode(app, tools, category_name, count):
    from .ui.display_manager import display_list_mode
    display_list_mode(app, tools, category_name, count)