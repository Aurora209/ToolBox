# File: ToolBox/app/services/category_service.py

from pathlib import Path


def get_current_scan_info(app):
    """获取当前扫描信息"""
    if app.showing_all_tools:
        return Path(app.get_app_dir() / "ToolBox"), "所有工具", True
    
    cat_name = app.config['Categories'].get(str(app.current_category), f"分类{app.current_category}")
    base = Path(app.get_app_dir() / "ToolBox") / cat_name
    
    if app.current_subcategory:
        return base / app.current_subcategory, f"{cat_name} - {app.current_subcategory}", False
    return base, cat_name, False


def get_subcategories_for_category(app, cat_id):
    """获取指定分类的子分类"""
    subs = []
    try:
        name = app.config['Categories'].get(str(cat_id), f"分类{cat_id}")
        cat_dir = app.get_app_dir() / "ToolBox" / name
        if cat_dir.exists() and cat_dir.is_dir():
            for d in cat_dir.iterdir():
                if d.is_dir():
                    subs.append(d.name)
    except Exception as e:
        print(f"读取二级分类失败: {e}")
    return sorted(subs)


def load_and_display_tools(app):
    """加载并显示工具"""
    dir_path, display_name, is_all = get_current_scan_info(app)
    
    if is_all:
        load_and_display_all_tools(app)
        return
    
    tools = app.scan_directory(dir_path, display_name)
    
    search_text = app.search_var.get().lower()
    if search_text:
        tools = [t for t in tools if search_text in t['name'].lower() or search_text in t['ext']]
    
    type_filter = app.filetype_var.get()
    if type_filter != "全部":
        tools = [t for t in tools if t['type'] == type_filter]
    
    app.current_displayed_tools = tools
    app.display_tools_grid(tools, display_name, len(tools))


def load_and_display_all_tools(app):
    """加载并显示所有工具"""
    all_tools = []
    base = Path(app.get_app_dir() / "ToolBox")
    if base.exists():
        for cat_dir in base.iterdir():
            if cat_dir.is_dir():
                cat_name = cat_dir.name
                all_tools.extend(app.scan_directory(cat_dir, cat_name))
                for sub_dir in cat_dir.iterdir():
                    if sub_dir.is_dir():
                        all_tools.extend(app.scan_directory(sub_dir, f"{cat_name} - {sub_dir.name}"))
    
    search_text = app.search_var.get().lower()
    if search_text:
        all_tools = [t for t in all_tools if search_text in t['name'].lower()]
    if app.filetype_var.get() != "全部":
        all_tools = [t for t in all_tools if t['type'] == app.filetype_var.get()]
    
    app.current_displayed_tools = all_tools
    app.display_tools_grid(all_tools, "所有工具", len(all_tools))