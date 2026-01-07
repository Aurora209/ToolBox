# File: ToolBox/app/ui/category_manager.py

def on_tree_select(app, event=None):
    """处理分类树选择事件：一级分类=汇总二级目录；二级分类=只显示当前目录"""
    tree = getattr(app, "category_tree", None) or getattr(app, "tree", None)
    if tree is None:
        return

    sel = tree.selection()
    if not sel:
        return

    item_id = sel[0]
    parent_id = tree.parent(item_id)

    # 读取该节点绑定的路径（values[0]）
    values = tree.item(item_id, "values") or []
    selected_path = values[0] if values else None
    if not selected_path:
        # 没有路径就回退到 storage 根
        selected_path = getattr(app, "storage_path", None)

    # 标记当前选择层级：一级=1，二级=2
    # parent 为空表示一级分类
    app.selected_category_depth = 1 if parent_id == "" else 2
    app.selected_category_path = selected_path
    app.showing_all_tools = False

    # 触发加载显示（你 app.py 里已有 load_and_display_tools 方法）
    try:
        app.load_and_display_tools()
    except Exception:
        # 兜底：直接调用 service（避免某些版本的 app.load_and_display_tools 依赖 tree 未初始化）
        try:
            from ..services.category_service import load_and_display_tools
            load_and_display_tools(app, selected_path)
        except Exception as e:
            print(f"on_tree_select: 加载显示失败: {e}")


def show_all_tools(app):
    """显示所有工具"""
    app.showing_all_tools = True
    app.selected_category_depth = 0
    app.selected_category_path = getattr(app, "storage_path", None)

    # 清除树形控件选择
    tree = getattr(app, "category_tree", None) or getattr(app, "tree", None)
    if tree is not None:
        try:
            tree.selection_remove(tree.selection())
        except Exception:
            pass

    try:
        app.load_and_display_all_tools()
    except Exception:
        try:
            from ..services.category_service import load_and_display_all_tools
            load_and_display_all_tools(app)
        except Exception as e:
            print(f"show_all_tools: 显示所有工具失败: {e}")
