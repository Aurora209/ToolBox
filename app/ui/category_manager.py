# File: ToolBox/app/ui/category_manager.py

def on_tree_select(app, event):
    """处理分类树选择事件"""
    # 保护性检查：如果没有选择项，直接返回（避免 IndexError）
    sel = app.category_tree.selection()
    if not sel:
        return

    item = sel[0]
    item_text = app.category_tree.item(item, "text")

    # 检查是否为子分类
    is_subcategory = app.category_tree.parent(item) != ""

    if is_subcategory:
        # 获取主分类ID
        parent_item = app.category_tree.parent(item)
        parent_text = app.category_tree.item(parent_item, "text")

        # 获取主分类ID（从配置中）
        for i in range(1, int(app.config['Categories'].get('count', '0')) + 1):
            cat_name = app.config['Categories'].get(str(i), f"分类{i}")
            if f"📁 {cat_name}" in parent_text:
                app.current_category = i
                app.current_subcategory = item_text.replace("  📂 ", "")
                break
    else:
        # 主分类
        for i in range(1, int(app.config['Categories'].get('count', '0')) + 1):
            cat_name = app.config['Categories'].get(str(i), f"分类{i}")
            if f"📁 {cat_name}" in item_text:
                app.current_category = i
                app.current_subcategory = ""
                break

    app.load_and_display_tools()


def on_tree_double_click(app, event):
    """处理分类树双击事件"""
    # 保护性检查：防止双击事件触发但没有选择项
    sel = app.category_tree.selection()
    if not sel:
        return

    item = sel[0]
    item_text = app.category_tree.item(item, "text")

    # 检查是否为子分类
    is_subcategory = app.category_tree.parent(item) != ""

    if is_subcategory:
        # 获取主分类ID
        parent_item = app.category_tree.parent(item)
        parent_text = app.category_tree.item(parent_item, "text")

        # 获取主分类ID（从配置中）
        for i in range(1, int(app.config['Categories'].get('count', '0')) + 1):
            cat_name = app.config['Categories'].get(str(i), f"分类{i}")
            if f"📁 {cat_name}" in parent_text:
                app.current_category = i
                app.current_subcategory = item_text.replace("  📂 ", "")
                break
    else:
        # 主分类
        for i in range(1, int(app.config['Categories'].get('count', '0')) + 1):
            cat_name = app.config['Categories'].get(str(i), f"分类{i}")
            if f"📁 {cat_name}" in item_text:
                app.current_category = i
                app.current_subcategory = ""
                break

    app.load_and_display_tools()


def select_category(app, category_id):
    """选择指定分类"""
    app.current_category = category_id
    app.current_subcategory = ""
    
    # 在树形控件中选择对应的项目
    items = app.category_tree.get_children()
    if category_id <= len(items):
        app.category_tree.selection_set(items[category_id - 1])
        app.category_tree.focus(items[category_id - 1])
    
    app.load_and_display_tools()


def show_all_tools(app):
    """显示所有工具"""
    app.showing_all_tools = True
    app.current_category = 0
    app.current_subcategory = ""
    
    # 清除树形控件的选择
    app.category_tree.selection_remove(app.category_tree.selection())
    
    app.load_and_display_all_tools()