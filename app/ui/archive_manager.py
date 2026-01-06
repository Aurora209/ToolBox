def show_archive_manager(self):
    """显示压缩包管理界面"""
    from tkinter import Toplevel, Label, Frame, Button
    import tkinter.ttk as ttk
    from pathlib import Path

    # 创建新窗口
    win = Toplevel(self.root)
    win.title("压缩包管理")
    win.geometry("1000x600")
    win.transient(self.root)
    win.grab_set()

    # 创建表头和表格框架
    table_frame = Frame(win)
    table_frame.pack(fill='both', expand=True, padx=10, pady=10)

    # 创建Treeview
    columns = ('序号', '压缩包名称', '路径', '大小', '修改时间', '分类')
    tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

    # 定义列标题和宽度
    column_widths = {'序号': 60, '压缩包名称': 200, '路径': 300, '大小': 100, '修改时间': 150, '分类': 100}
    
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

    # 扫描所有分类中的压缩包文件
    all_archives = []
    base = Path(self.get_app_dir() / "Storage")
    if base.exists():
        for cat_dir in base.iterdir():
            if cat_dir.is_dir():
                cat_name = cat_dir.name
                # 扫描主分类目录
                archives = self.scan_directory_for_archives(cat_dir, cat_name)
                all_archives.extend(archives)
                
                # 扫描子分类目录
                for sub_dir in cat_dir.iterdir():
                    if sub_dir.is_dir():
                        sub_archives = self.scan_directory_for_archives(sub_dir, f"{cat_name} - {sub_dir.name}")
                        all_archives.extend(sub_archives)

    # 插入数据
    for idx, archive in enumerate(all_archives, 1):
        tree.insert('', 'end', values=(
            idx,
            archive['name'],
            archive['path'],
            archive['size'],
            archive['mtime'],
            archive['category']
        ))

    # 双击解压交互：双击某行直接解压
    def on_double(event):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])['values']
        if len(vals) >= 3:
            path = vals[2]
            extract_archive(self, path)

    tree.bind("<Double-1>", on_double)

    # 添加关闭按钮
    button_frame = Frame(win)
    button_frame.pack(fill='x', padx=10, pady=10)
    Button(button_frame, text="关闭", command=win.destroy, width=10).pack(side='right')