# File: ToolBox/app/services/display_service.py

from ..ui.display_manager import display_list_mode, display_grid_mode

def display_tools_grid(app, tools, category_name, count):
    """
    显示工具（保持旧接口不变）
    根据 app.display_mode 决定调用 grid 或 list
    """
    mode = getattr(app, 'display_mode', 'list') or 'list'
    if mode == 'grid':
        display_grid_mode(app, tools, category_name, count)
    else:
        display_list_mode(app, tools, category_name, count)
