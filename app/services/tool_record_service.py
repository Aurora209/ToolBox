def show_tools_added_record(app):
    """显示工具添加记录"""
    from tkinter import Toplevel, Label, Frame, Button
    import tkinter.ttk as ttk
    
    # 创建新窗口
    win = Toplevel(app.root)
    win.title("工具添加记录")
    win.geometry("1200x600")
    win.transient(app.root)
    win.grab_set()

    # 创建表头和表格框架
    table_frame = Frame(win)
    table_frame.pack(fill='both', expand=True, padx=10, pady=10)

    # 创建Treeview
    columns = ('序号', '工具名称', '分类', '版本', '添加时间', '类型', '备注')
    tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

    # 定义列标题和宽度
    column_widths = {'序号': 60, '工具名称': 200, '分类': 100, '版本': 100, '添加时间': 150, '类型': 100, '备注': 200}
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=column_widths[col], anchor='w')

    # 添加滚动条
    v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

    # 布局
    tree.grid(row=0, column=0, sticky='nsew')
    v_scrollbar.grid(row=0, column=1, sticky='ns')
    h_scrollbar.grid(row=1, column=0, sticky='ew')

    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    # 存储排序状态和当前分类筛选
    sort_reverse = [False]  # 使用列表以便在内部函数中修改
    current_category_filter = [None]  # 当前分类筛选
    
    def sort_by_time():
        """按添加时间排序"""
        sort_reverse[0] = not sort_reverse[0]
        update_display(current_category_filter[0], sort_by_time=True, reverse=sort_reverse[0])

    def filter_by_category():
        """按分类筛选"""
        # 创建分类选择窗口
        category_win = Toplevel(win)
        category_win.title("选择分类")
        category_win.geometry("300x300")
        category_win.transient(win)
        category_win.grab_set()
        
        Label(category_win, text="请选择要筛选的分类:", font=("Microsoft YaHei", 10)).pack(pady=10)
        
        # 获取所有唯一分类
        categories = set()
        for record in app.tools_added_record.values():
            categories.add(record['category'])
        categories = sorted(list(categories))
        
        # 添加"全部"选项
        categories.insert(0, "全部")
        
        listbox = ttk.Treeview(category_win, columns=('分类',), show='tree headings', height=10)
        listbox.heading('#0', text='选择')
        listbox.heading('分类', text='分类')
        listbox.column('#0', width=50)
        listbox.column('分类', width=200)
        
        for cat in categories:
            listbox.insert('', 'end', text='', values=(cat,))
        
        listbox.pack(fill='both', expand=True, padx=10, pady=10)
        
        def select_category():
            selection = listbox.selection()
            if selection:
                selected_item = listbox.item(selection[0])
                selected_cat = selected_item['values'][0]
                if selected_cat == "全部":
                    current_category_filter[0] = None
                else:
                    current_category_filter[0] = selected_cat
                update_display(current_category_filter[0])
            category_win.destroy()
        
        Button(category_win, text="确定", command=select_category).pack(pady=10)

    # 为"添加时间"和"分类"列头绑定点击事件
    tree.heading('添加时间', text='添加时间', command=sort_by_time)
    tree.heading('分类', text='分类', command=filter_by_category)
    
    def update_display(category_filter=None, sort_by_time=False, reverse=False):
        """更新显示内容"""
        # 清空现有数据
        for item in tree.get_children():
            tree.delete(item)
        
        # 过滤记录
        filtered_records = []
        for path, record in app.tools_added_record.items():
            if category_filter is None or record['category'] == category_filter:
                filtered_records.append((path, record))
        
        # 排序
        if sort_by_time:
            filtered_records.sort(key=lambda x: x[1]['add_time'], reverse=reverse)
        
        # 插入数据
        for idx, (path, record) in enumerate(filtered_records, 1):
            tree.insert('', 'end', values=(
                idx,
                record['name'],
                record['category'],
                record['version'],
                record['add_time'],
                record['type'],
                record['note']
            ))

    # 初始显示
    update_display()

    # 添加关闭按钮
    button_frame = Frame(win)
    button_frame.pack(fill='x', padx=10, pady=10)
    Button(button_frame, text="关闭", command=win.destroy, width=10).pack(side='right')