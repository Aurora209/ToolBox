import os
import json
from tkinter import messagebox

def scan_categories(storage_path):
    """扫描目录以获取所有分类"""
    categories = []
    
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
        return categories
    
    for root, dirs, files in os.walk(storage_path):
        # 获取当前目录相对于storage_path的路径
        rel_path = os.path.relpath(root, storage_path)
        if rel_path == '.':
            category_name = '根目录'
        else:
            # 使用路径的最后一级作为分类名
            category_name = rel_path.replace(os.sep, ' > ')
        
        # 查找当前目录下的.py文件作为工具
        tools = []
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                tool_path = os.path.join(root, file)
                tool_info = extract_tool_info(tool_path)
                if tool_info:
                    tools.append({
                        'name': tool_info.get('name', file),
                        'description': tool_info.get('description', ''),
                        'path': tool_path,
                        'filename': file
                    })
        
        if tools or dirs:  # 如果有工具或子目录，添加这个分类
            categories.append({
                'name': category_name,
                'path': root,
                'tools': tools
            })
    
    return categories

def extract_tool_info(tool_path):
    """从工具文件中提取信息"""
    try:
        with open(tool_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找包含信息的注释
        lines = content.split('\n')
        info = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('# NAME:'):
                info['name'] = line[7:].strip()
            elif line.startswith('# DESC:') or line.startswith('# DESCRIPTION:'):
                info['description'] = line[7:].strip() if line.startswith('# DESC:') else line[13:].strip()
            
            # 如果已经找到所有信息，可以提前退出
            if 'name' in info and 'description' in info:
                break
        
        # 如果没有找到名称，使用文件名
        if 'name' not in info:
            info['name'] = os.path.basename(tool_path)[:-3]  # 去掉.py后缀
        
        return info
    except Exception as e:
        print(f"扫描目录 {tool_path} 时出错: {e}")
        return None

def load_and_display_tools(app, selected_category_path):
    """加载并显示选中分类的工具"""
    # 检查UI组件是否已初始化
    if not hasattr(app, 'main_frame') or app.main_frame is None:
        print("main_frame 未初始化，延迟调用直到UI组件初始化完成")
        # 延迟执行，等待UI组件完全初始化
        app.root.after(100, lambda: safe_display_tools_grid_with_delay(app, selected_category_path))
        return
    
    # 确保存储路径已初始化
    if not hasattr(app, 'storage_path'):
        app.storage_path = str(app.get_app_dir() / "Storage")
    
    # 检查selected_category_path是否在storage_path下，如果不是则使用storage_path
    storage_path = app.storage_path
    if not selected_category_path.startswith(storage_path):
        print(f"警告: 选中的路径 {selected_category_path} 不在存储路径 {storage_path} 下，使用存储路径")
        selected_category_path = storage_path
    
    # 检查路径是否存在
    if not os.path.exists(selected_category_path):
        print(f"路径不存在: {selected_category_path}")
        # 如果路径不存在，显示空列表
        app.display_tools_grid([], "未找到路径", 0)
        return
    
    # 扫描选中分类目录下的工具（支持多种文件类型，而不仅限于 .py）
    tools = []
    if os.path.exists(selected_category_path):
        for file in os.listdir(selected_category_path):
            full_path = os.path.join(selected_category_path, file)
            # 仅处理文件（可扩展为目录）
            if os.path.isfile(full_path) and file != '__init__.py':
                ext = os.path.splitext(file)[1].lower()
                if ext == '.py':
                    tool_info = extract_tool_info(full_path)
                    name = tool_info.get('name', file) if tool_info else os.path.splitext(file)[0]
                    desc = tool_info.get('description', '') if tool_info else ''
                else:
                    name = os.path.splitext(file)[0]
                    desc = ''

                tools.append({
                    'name': name,
                    'description': desc,
                    'path': full_path,
                    'filename': file,
                    'ext': ext,
                    'type': app.get_file_type_category(ext) if hasattr(app, 'get_file_type_category') else ''
                })
            # 如果需要显示子目录作为特殊项，也可以添加
    
    # 获取显示名称 - 将路径转换为层级名称
    rel_path = os.path.relpath(selected_category_path, storage_path)
    if rel_path == '.':
        display_name = '根目录'
    else:
        display_name = rel_path.replace(os.sep, ' > ')
    
    # 把 display_name 作为 category 字段填充到每个工具（保证列表模式能显示分类）
    for t in tools:
        t['category'] = display_name

    # 文件类型过滤变量（可能未在某些 UI 模式中存在）
    filetype_var = getattr(app, 'filetype_var', None)
    if filetype_var is not None and filetype_var.get() != "全部":
        selected = filetype_var.get()
        tools = [t for t in tools if t.get('type') == selected]

    app.display_tools_grid(tools, display_name, len(tools))

def safe_display_tools_grid_with_delay(app, selected_category_path):
    """延迟安全地显示工具网格，确保main_frame已初始化"""
    if hasattr(app, 'main_frame') and app.main_frame is not None:
        load_and_display_tools(app, selected_category_path)
    else:
        print("错误：main_frame 仍未初始化，无法显示工具")

def safe_display_tools_grid(app, tools, display_name, count):
    """安全地显示工具网格，确保main_frame已初始化"""
    if hasattr(app, 'main_frame') and app.main_frame is not None:
        app.display_tools_grid(tools, display_name, count)
    else:
        print("错误：main_frame 仍未初始化，无法显示工具")

def get_current_scan_info(app):
    """获取当前选中的分类信息。

    返回三元组 (path, display_name, is_all)：
    - path: 选中分类的文件系统路径，若未选中则返回 storage_path
    - display_name: 用于显示的名称（如 '根目录' 或层级名）
    - is_all: 如果当前处于“所有工具”模式返回 True（表示拖放不允许）
    """
    # 确保 storage_path 已初始化
    if not hasattr(app, 'storage_path'):
        app.storage_path = str(app.get_app_dir() / "Storage")  # 临时补救措施

    # 如果处于显示“所有工具”的模式，视为不可拖放目标
    if getattr(app, 'showing_all_tools', False):
        return (None, '所有工具', True)

    # 检查 tree 控件是否已初始化
    if not hasattr(app, 'tree') or app.tree is None:
        print("错误：tree控件尚未初始化")
        # 回退到 storage_path，允许拖放到根目录
        rel = '根目录'
        return (app.storage_path, rel, False)

    # 返回当前选中的分类路径和相关信息
    selection = app.tree.selection()
    if selection:
        item = app.tree.item(selection[0])
        category_path = item['values'][0] if item['values'] else None
        if category_path:
            rel_path = os.path.relpath(category_path, app.storage_path)
            if rel_path == '.':
                display_name = '根目录'
            else:
                display_name = rel_path.replace(os.sep, ' > ')
            return (category_path, display_name, False)

    # 如果没有选择，则返回根目录信息
    return (app.storage_path, '根目录', False)

def get_subcategories_for_category(app, cat_id):
    """获取指定分类的子分类。

    优先使用配置中的 `Subcategories`（键形如 "<主分类索引>_<序号>"），返回二级分类名称列表；
    如果传入的是路径或需要回退时，则扫描文件系统并返回目录名列表。
    """
    # 确保 storage_path 已初始化
    if not hasattr(app, 'storage_path'):
        app.storage_path = str(app.get_app_dir() / "Storage")  # 临时补救措施

    storage_path = app.storage_path

    # 如果 cat_id 是整数（主分类索引），从配置中读取二级分类
    try:
        idx = int(cat_id)
        subs = []
        entries = []
        for k in app.config['Subcategories']:
            if k.startswith(f"{idx}_"):
                try:
                    num = int(k.split("_", 1)[1])
                except Exception as exc:
                    print(f"读取子分类编号失败: {k} ({exc})")
                    num = 0
                entries.append((num, app.config['Subcategories'][k]))
        entries.sort(key=lambda x: x[0])
        for _, name in entries:
            subs.append(name)
        return subs
    except (ValueError, TypeError):
        # 非整数，继续执行下方的回退逻辑
        pass

    # 回退：如果传入的是 'root' 或路径字符串，扫描对应目录并返回子目录名列表
    if cat_id == 1 or cat_id == "root":  # 假设1或"root"代表根分类
        parent_path = storage_path
    elif isinstance(cat_id, str) and os.path.exists(cat_id):
        parent_path = cat_id
    else:
        parent_path = storage_path

    subcategories = []
    if os.path.exists(parent_path) and os.path.isdir(parent_path):
        for item in os.listdir(parent_path):
            item_path = os.path.join(parent_path, item)
            if os.path.isdir(item_path):
                subcategories.append(item)

    return subcategories

def load_and_display_all_tools(app):
    """加载并显示所有工具 - 显示根目录下所有工具（包括子目录）"""
    # 确保 storage_path 已初始化
    if not hasattr(app, 'storage_path'):
        app.storage_path = str(app.get_app_dir() / "Storage")  # 临时补救措施
    
    # 扫描整个存储目录下的所有工具
    all_tools = []
    storage_path = app.storage_path
    
    for root, dirs, files in os.walk(storage_path):
        for file in files:
            if file != '__init__.py':
                tool_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                if ext == '.py':
                    tool_info = extract_tool_info(tool_path)
                    name = tool_info.get('name', file) if tool_info else os.path.splitext(file)[0]
                    desc = tool_info.get('description', '') if tool_info else ''
                else:
                    name = os.path.splitext(file)[0]
                    desc = ''

                # 计算相对于存储路径的目录名作为分类名
                rel_path = os.path.relpath(root, storage_path)
                if rel_path == '.':
                    category_name = '根目录'
                else:
                    category_name = rel_path.replace(os.sep, ' > ')
                
                all_tools.append({
                    'name': name,
                    'description': desc,
                    'path': tool_path,
                    'filename': file,
                    'ext': ext,
                    'type': app.get_file_type_category(ext) if hasattr(app, 'get_file_type_category') else '',
                    'category': category_name
                })
    
    # 应用搜索与类型过滤（如果存在）
    query = getattr(app, 'search_var', None)
    if query is not None and query.get().strip():
        q = query.get().strip().lower()
        all_tools = [t for t in all_tools if q in t.get('name', '').lower() or q in t.get('filename', '').lower() or q in t.get('description', '').lower()]

    filetype_var = getattr(app, 'filetype_var', None)
    if filetype_var is not None and filetype_var.get() != "全部":
        selected = filetype_var.get()
        all_tools = [t for t in all_tools if t.get('type') == selected]

    # 显示所有工具
    app.display_tools_grid(all_tools, '所有工具', len(all_tools))
