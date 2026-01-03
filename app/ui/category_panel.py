# File: ToolBox/app/ui/category_panel.py

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
    
    style = ttk.Style()
    style.configure("Treeview", font=("Microsoft YaHei", 10), rowheight=30)
    style.configure("Treeview.Heading", font=("Microsoft YaHei", 10, "bold"))
    
    app.category_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
    app.category_tree.pack(side='left', fill='both', expand=True)
    
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
    for item in tree.get_children():
        tree.delete(item)
    
    try:
        count = int(app.config['Categories'].get('count', '0'))
    except:
        count = 0
    
    for i in range(1, count + 1):
        cat_name = app.config['Categories'].get(str(i), f"分类{i}")
        cat_id = tree.insert("", "end", text=f"📁 {cat_name}", open=False, tags=("main",))
        
        subs = app.get_subcategories_for_category(i)
        if subs:
            for sub in subs:
                tree.insert(cat_id, "end", text=f"  📂 {sub}", tags=("sub",))