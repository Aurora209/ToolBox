# File: ToolBox/app/ui/category_panel.py

import os
from tkinter import Frame, Label, Button
from tkinter import ttk

def create_category_panel(app, parent):
    category_frame = Frame(parent, bg='#ecf0f1', width=250, relief='raised', bd=2)
    category_frame.pack(side='left', fill='y', padx=(0, 10))
    category_frame.pack_propagate(False)
    
    Label(category_frame, text="分类导航", font=("Microsoft YaHei", 14, "bold"),
          bg='#ecf0f1', fg='#2c3e50').pack(pady=15)
    
    tree_frame = Frame(category_frame, bg='#ecf0f1')
    tree_frame.pack(fill='both', expand=True, padx=10)
    # 暴露给 app 以便其他模块在清理界面时保留该框架
    app.tree_frame = tree_frame
    
    style = ttk.Style()
    style.configure("Treeview", font=("Microsoft YaHei", 10), rowheight=30)
    style.configure("Treeview.Heading", font=("Microsoft YaHei", 10, "bold"))
    
    app.category_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
    app.category_tree.pack(side='left', fill='both', expand=True)
    # 兼容旧代码和其它模块，对外同时提供 app.tree 引用
    app.tree = app.category_tree
    
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=app.category_tree.yview)
    scrollbar.pack(side='right', fill='y')
    app.category_tree.configure(yscrollcommand=scrollbar.set)
    
    function_frame = Frame(category_frame, bg='#ecf0f1')
    function_frame.pack(fill='x', padx=10, pady=10)
    
    app.all_tools_btn = Button(function_frame, text="全部工具",
                               font=("Microsoft YaHei", 11),
                               bg='#7f8c8d', fg='white', relief='flat',
                               command=app.show_all_tools)
    app.all_tools_btn.pack(fill='x', pady=2)
    
    Button(function_frame, text="工具记录",
           font=("Microsoft YaHei", 11),
           bg='#9b59b6', fg='white', relief='flat',
           command=app.show_tools_record).pack(fill='x', pady=2)
    
    Button(function_frame, text="压缩包管理",
           font=("Microsoft YaHei", 11),
           bg='#e67e22', fg='white', relief='flat',
           command=app.show_archive_manager).pack(fill='x', pady=2)
    
    Button(function_frame, text="自动记录设置",
           font=("Microsoft YaHei", 11),
           bg='#e74c3c', fg='white', relief='flat',
           command=app.show_auto_record_settings).pack(fill='x', pady=2)
    
    Button(function_frame, text="分类设置",
           font=("Microsoft YaHei", 11),
           bg='#3498db', fg='white', relief='flat',
           command=app.show_category_settings).pack(fill='x', pady=(2, 0))
    
    app.category_tree.bind("<<TreeviewSelect>>", app.on_tree_select)
    app.category_tree.bind("<Double-1>", app.on_tree_double_click)
    
    app.refresh_category_tree()

def refresh_category_tree(app):
    tree = app.category_tree
    # 日志：开始刷新分类树
    try:
        print("刷新分类树: 开始")
        print(f"当前 storage_path: {getattr(app, 'storage_path', None)}")
        count_val = app.config['Categories'].get('count', '0')
        print(f"配置中的 Categories.count = {count_val}")
    except Exception as e:
        print(f"刷新分类树：读取配置信息失败：{e}")

    for item in tree.get_children():
        tree.delete(item)
    
    try:
        count = int(app.config['Categories'].get('count', '0'))
    except Exception as exc:
        print(f"解析分类数量失败: {exc}")
        count = 0
    
    print(f"将插入 {count} 个主分类")
    for i in range(1, count + 1):
        cat_name = app.config['Categories'].get(str(i), f"分类{i}")
        # 生成主分类路径并保存到 item values 中，便于选择时直接读取路径
        cat_path = os.path.join(app.storage_path, cat_name) if hasattr(app, 'storage_path') else cat_name
        print(f"插入主分类: {cat_name} -> {cat_path}")
        cat_id = tree.insert("", "end", text=f"📁 {cat_name}", open=False, tags=("main",), values=(cat_path,))
        
        subs = app.get_subcategories_for_category(i)
        if subs:
            for sub in subs:
                # subs 返回子分类名（如配置中定义），构造完整路径作为 values
                sub_path = os.path.join(cat_path, sub)
                print(f"  插入子分类: {sub} -> {sub_path}")
                tree.insert(cat_id, "end", text=f"  📂 {sub}", tags=("sub",), values=(sub_path,))
    print("刷新分类树: 完成")
