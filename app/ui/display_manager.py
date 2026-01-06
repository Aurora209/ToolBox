import tkinter as tk
from tkinter import ttk
import subprocess
import os
from ..utils.tool_manager import run_tool as util_run_tool

def display_list_mode(app, tools, category_name, count):
    """以 Excel 风格的多列表格显示工具（在右侧的 tools_container 中渲染）。
    列：名称、类型、大小、修改时间、路径；支持列排序与双击运行。"""
    import datetime

    # 使用 tools_container（回退到 main_frame）
    container = getattr(app, 'tools_container', app.main_frame)

    # 清除容器现有内容
    for widget in container.winfo_children():
        widget.destroy()

    # 标题栏
    header = ttk.Frame(container)
    header.pack(fill='x', padx=6, pady=(6, 0))
    title_label = ttk.Label(header, text=f"{category_name} （{count}）", font=('Microsoft YaHei', 10, 'bold'))
    title_label.pack(side='left')

    # Treeview（多列） —— 使用你指定的列顺序：序号, 名称, 分类, 版本, 添加时间, 类型, 备注
    columns = ('idx', 'name', 'category', 'version', 'add_time', 'type', 'note')
    tree = ttk.Treeview(container, columns=columns, show='headings')

    # 样式与列配置
    tree.heading('idx', text='序号')
    tree.heading('name', text='名称')
    tree.heading('category', text='分类')
    tree.heading('version', text='版本')
    tree.heading('add_time', text='添加时间')
    tree.heading('type', text='类型')
    tree.heading('note', text='备注')

    tree.column('idx', width=60, anchor='center')
    tree.column('name', width=260, anchor='w')
    tree.column('category', width=140, anchor='w')
    tree.column('version', width=100, anchor='center')
    tree.column('add_time', width=140, anchor='center')
    tree.column('type', width=100, anchor='center')
    tree.column('note', width=320, anchor='w')

    vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.pack(fill='both', expand=True, side='left', padx=(6,0), pady=6)
    vsb.pack(side='right', fill='y')
    hsb.pack(side='bottom', fill='x')

    # Helper: 格式化大小与时间
    def fmt_size(n):
        try:
            n = int(n)
        except Exception:
            return ''
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024:
                return f"{n}{unit}"
            n = n // 1024
        return f"{n}TB"

    def fmt_time(ts):
        try:
            dt = datetime.datetime.fromtimestamp(float(ts))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return ''

    # 插入数据 —— 填充序号、名称、分类（一级）、版本、添加时间、类型、备注
    # 准备内部映射用于双击运行时查找真实磁盘路径（不在表格中显示）
    if not hasattr(app, '_list_item_map'):
        app._list_item_map = {}

    for idx, tool in enumerate(tools, start=1):
        p = tool.get('path', '')
        name = tool.get('name') or os.path.basename(p)

        # 分类：取一级分类（按 '>' 分割）
        raw_cat = tool.get('category', '')
        if isinstance(raw_cat, str) and raw_cat.strip():
            first_cat = raw_cat.split('>')[0].strip().strip()
        else:
            first_cat = ''

        # 版本、添加时间、备注优先从 tools_added_record 获取（优先使用相对 key）；若缺失则尝试从文件元数据获取并持久化记录
        version = '-'
        add_time = '-'
        note = tool.get('note', '') or ''
        try:
            rec = None
            rel_key = None
            # 尝试相对 storage_path 的 key，并使用规范化路径
            if hasattr(app, 'storage_path'):
                try:
                    rel_key = os.path.normpath(os.path.relpath(p, app.storage_path))
                    if not rel_key.startswith('..') and rel_key in getattr(app, 'tools_added_record', {}):
                        rec = app.tools_added_record.get(rel_key)
                except Exception:
                    rel_key = None

            # 再尝试绝对路径 key（也做规范化）
            norm_p = os.path.normpath(p)
            if rec is None and hasattr(app, 'tools_added_record') and norm_p in app.tools_added_record:
                rec = app.tools_added_record.get(norm_p)

            # 调试日志：如果未找到记录，打印关键路径与现有记录的部分键，帮助定位匹配问题
            if rec is None:
                try:
                    exist_keys = list(getattr(app, 'tools_added_record', {}).keys())[:12]
                    print(f"tools_added_record keys (sample): {exist_keys}")
                    print(f"lookup rel_key={rel_key!r}, norm_p={norm_p!r}, storage_path={getattr(app,'storage_path',None)!r}")
                except Exception:
                    pass

            if rec:
                # 使用记录中的值
                version = rec.get('version', '-') or '-'
                add_time = rec.get('add_time', '-') or '-'
                note = rec.get('note', '') or note

                # 如果记录缺失关键信息，尝试从文件元数据回填并持久化
                updated = False
                try:
                    # 版本回填
                    if (not version or version == '-' or version == '未知') and os.path.exists(p):
                        ext = os.path.splitext(p)[1].lower()
                        if ext in ('.exe', '.msi') and hasattr(app, 'get_file_version_info'):
                            try:
                                vi = app.get_file_version_info(p)
                                if vi and 'file_version' in vi:
                                    version = vi.get('file_version')
                                    rec['version'] = version
                                    updated = True
                                elif vi and 'product_version' in vi:
                                    version = vi.get('product_version')
                                    rec['version'] = version
                                    updated = True
                                else:
                                    # 标记为已探测但未知
                                    version = '未知'
                            except Exception:
                                pass

                    # 添加时间回填
                    if (not add_time or add_time == '-' or add_time is None) and os.path.exists(p):
                        try:
                            ct = os.path.getctime(p)
                            from datetime import datetime as _dt
                            add_time = _dt.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M:%S')
                            rec['add_time'] = add_time
                            updated = True
                        except Exception:
                            pass

                    # 持久化更新到配置（使用命中的键）
                    if updated:
                        # 找到配置中的 key（相对优先）
                        key_in_conf = None
                        try:
                            if hasattr(app, 'storage_path'):
                                rel_key_try = os.path.normpath(os.path.relpath(p, app.storage_path))
                                if not rel_key_try.startswith('..') and rel_key_try in app.config['ToolAddedRecord']:
                                    key_in_conf = rel_key_try
                        except Exception:
                            pass
                        if key_in_conf is None:
                            # 尝试匹配绝对路径
                            if norm_p in app.config['ToolAddedRecord']:
                                key_in_conf = norm_p

                        if key_in_conf:
                            parts = app.config['ToolAddedRecord'].get(key_in_conf, '').split('|', 5)
                            if len(parts) == 6:
                                parts[2] = rec.get('add_time', parts[2])
                                parts[4] = rec.get('note', parts[4])
                                parts[5] = rec.get('version', parts[5])
                                app.config['ToolAddedRecord'][key_in_conf] = '|'.join(parts)
                                try:
                                    app.config_manager.save_config()
                                except Exception:
                                    pass
                except Exception:
                    pass
            else:
                # 未找到记录：尝试从文件获取信息（ctime，版本）并记录
                try:
                    # 调试：打印文件存在性与扩展名信息
                    exists = os.path.exists(p)
                    ext = os.path.splitext(p)[1].lower()
                    print(f"未找到记录，准备读取文件元数据: path={p}, exists={exists}, ext={ext}, has_record_tool={hasattr(app,'record_tool_added')}, has_get_ver={hasattr(app,'get_file_version_info')}")

                    if exists:
                        # 添加时间使用创建时间（Windows 上是复制/创建时间）
                        ct = os.path.getctime(p)
                        from datetime import datetime as _dt
                        add_time = _dt.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M:%S')

                        # 版本信息针对 exe/msi
                        if ext in ('.exe', '.msi') and hasattr(app, 'get_file_version_info'):
                            try:
                                vi = app.get_file_version_info(p)
                                print(f"get_file_version_info 返回: {vi}")
                                if vi and 'file_version' in vi:
                                    version = vi.get('file_version')
                                elif vi and 'product_version' in vi:
                                    version = vi.get('product_version')
                                else:
                                    version = '未知'
                            except Exception as e:
                                print(f"读取版本信息失败: {e}")
                                version = '未知'

                        # 将信息持久化到记录中，使用 app.record_tool_added（会使用相对 key）
                        try:
                            # category 计算为一级分类名
                            cat_name = ''
                            if hasattr(app, 'storage_path'):
                                try:
                                    dir_rel = os.path.normpath(os.path.relpath(os.path.dirname(p), app.storage_path))
                                    if dir_rel == '.':
                                        cat_name = '根目录'
                                    else:
                                        cat_name = dir_rel.split(os.sep)[0]
                                except Exception:
                                    pass

                            if hasattr(app, 'record_tool_added'):
                                try:
                                    print(f"尝试创建记录: path={p}, name={name}, cat={cat_name}, note={note}")
                                    app.record_tool_added(p, name, cat_name, note)
                                    print("调用 record_tool_added 后，tools_added_record keys count:", len(getattr(app,'tools_added_record', {})))
                                except Exception as e:
                                    print(f"调用 record_tool_added 失败: {e}")

                                # 记录已创建（如果成功），尝试重新读取以回填显示值
                                try:
                                    # 优先用相对 key
                                    if hasattr(app, 'storage_path'):
                                        new_key = os.path.normpath(os.path.relpath(p, app.storage_path))
                                        if not new_key.startswith('..') and new_key in app.tools_added_record:
                                            new_rec = app.tools_added_record.get(new_key)
                                        else:
                                            new_rec = app.tools_added_record.get(norm_p)
                                    else:
                                        new_rec = app.tools_added_record.get(norm_p)

                                    if new_rec:
                                        version = new_rec.get('version', version)
                                        add_time = new_rec.get('add_time', add_time)
                                        note = new_rec.get('note', note)
                                        print(f"自动记录信息已创建: {p} -> version={version}, add_time={add_time}")
                                    else:
                                        print(f"创建记录后仍未在内存中找到记录: new_key={new_key!r}, norm_p={norm_p!r}")
                                except Exception as e:
                                    print(f"读取新记录失败: {e}")
                        except Exception:
                            pass
                except Exception as e:
                    print(f"尝试读取文件元数据并记录时发生异常: {e}")

        except Exception:
            pass

        # 类型显示为文件扩展名（不含点），回退到工具记录中的类型字段
        try:
            ttype = os.path.splitext(p)[1].lstrip('.').lower() or tool.get('type', '')
        except Exception:
            ttype = tool.get('type', '')

        # 插入行并保存映射
        iid = tree.insert('', 'end', values=(idx, name, first_cat, version, add_time, ttype, note))
        app._list_item_map[iid] = p

    # 双击运行
    def on_double_click(event):
        selected = tree.selection()
        if not selected:
            return
        iid = selected[0]
        path = app._list_item_map.get(iid)
        if path:
            util_run_tool(app, path)

    tree.bind('<Double-1>', on_double_click)

    # 右键菜单（在 Treeview 上显示）
    try:
        from .context_menu import show_tool_context_menu
        tree.bind('<Button-3>', lambda e: show_tool_context_menu(app, e, tree, tools))
    except Exception:
        pass

    # 列排序
    sort_state = {'col': None, 'reverse': False}

    def sort_by(col):
        # 获取所有行和对应值
        data = [(tree.set(k, col), k) for k in tree.get_children('')]

        # 根据列类型转换
        if col == 'add_time':
            from datetime import datetime
            def keyfunc(x):
                try:
                    return datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S')
                except Exception:
                    return datetime.min
        elif col == 'idx':
            def keyfunc(x):
                try:
                    return int(x[0])
                except Exception:
                    return -1
        else:
            def keyfunc(x):
                return (x[0] or '').lower()

        data.sort(key=keyfunc, reverse=sort_state['col'] == col and not sort_state['reverse'])

        # 更新顺序
        for index, (_, k) in enumerate(data):
            tree.move(k, '', index)

        # 更新序号显示（使序号反映当前行序）
        for new_idx, iid in enumerate(tree.get_children(''), start=1):
            vals = list(tree.item(iid, 'values'))
            vals[0] = new_idx
            tree.item(iid, values=vals)

        # 更新排序状态
        if sort_state['col'] == col:
            sort_state['reverse'] = not sort_state['reverse']
        else:
            sort_state['col'] = col
            sort_state['reverse'] = False

    # 绑定列头点击
    for c in columns:
        tree.heading(c, command=lambda _c=c: sort_by(_c))

    # 空状态提示
    if not tree.get_children(''):
        empty = ttk.Label(container, text='未找到任何工具或文件。', foreground='gray')
        empty.place(relx=0.5, rely=0.5, anchor='center')


def display_grid_mode(app, tools, category_name, count, cols=4):
    """以网格模式显示工具（每行 cols 个），仿 Windows 图标视图，支持图标大小调节与选择。"""
    container = getattr(app, 'tools_container', app.main_frame)

    # 清除容器现有内容
    for widget in container.winfo_children():
        widget.destroy()

    # 标题与图标大小控制
    header = ttk.Frame(container)
    header.pack(fill='x', padx=6, pady=(6, 0))
    title_label = ttk.Label(header, text=f"{category_name} （{count}）", font=('Microsoft YaHei', 10, 'bold'))
    title_label.pack(side='left')

    try:
        cur_size = int(app.config['General'].get('icon_size', '36'))
    except Exception:
        cur_size = 36
    size_var = tk.IntVar(value=cur_size)

    def on_size_change(val):
        try:
            size = int(float(val))
            app.config['General']['icon_size'] = str(size)
            try:
                app.config_manager.save_config()
            except Exception:
                pass
            # 重新渲染网格
            app.display_grid_mode(tools, category_name, count)
        except Exception:
            pass

    size_label = ttk.Label(header, text='图标大小:')
    size_label.pack(side='right', padx=(6, 0))
    size_scale = ttk.Scale(header, from_=24, to=96, orient='horizontal', variable=size_var, command=on_size_change)
    size_scale.pack(side='right')

    grid_frame = tk.Frame(container, bg='white')
    grid_frame.pack(fill='both', expand=True, padx=6, pady=6)

    # 让列可扩展
    for i in range(cols):
        grid_frame.grid_columnconfigure(i, weight=1)

    selected_item = {'widget': None, 'path': None}

    def select_item(widget, path):
        prev = selected_item['widget']
        if prev and prev.winfo_exists():
            try:
                prev.config(relief='raised', bd=1)
            except Exception:
                pass
        try:
            widget.config(relief='solid', bd=2)
        except Exception:
            pass
        selected_item['widget'] = widget
        selected_item['path'] = path

    row = 0
    col = 0
    icon_size = size_var.get()

    for idx, tool in enumerate(tools):
        item = tk.Frame(grid_frame, relief='raised', borderwidth=1, padx=4, pady=4, bg='white')
        item.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')

        # 图标
        try:
            icon = app.get_tool_icon(tool['path'], tool.get('name', ''), size=icon_size)
            if icon:
                l = tk.Label(item, image=icon, bg='white')
                l.image = icon
                l.pack()
            else:
                # 回退显示 emoji 或扩展名符号
                ext = os.path.splitext(tool.get('path', ''))[1].lower()
                from ..utils.icons import get_icon_for_filetype
                ft = app.get_file_type_category(ext) if hasattr(app, 'get_file_type_category') else ''
                sym = get_icon_for_filetype(ft, ext)
                tk.Label(item, text=sym, font=('Segoe UI Emoji', max(12, int(icon_size * 0.4))), bg='white').pack()
        except Exception:
            pass

        tk.Label(item, text=tool.get('name', ''), font=('Microsoft YaHei', 10), wraplength=int(icon_size * 1.5), bg='white').pack()

        # 操作按钮
        btn_frame = ttk.Frame(item)
        btn_frame.pack(pady=2)
        run_btn = ttk.Button(btn_frame, text='运行', command=lambda p=tool['path']: util_run_tool(app, p))
        run_btn.pack(side='left')

        # 绑定选择、双击与右键菜单
        item.bind('<Button-1>', lambda e, w=item, p=tool['path']: select_item(w, p))
        item.bind('<Double-1>', lambda e, p=tool['path']: util_run_tool(app, p))
        try:
            from .context_menu import add_context_menu
            add_context_menu(app, item, tool)
            item.bind('<Button-3>', lambda e, w=item, t=tool: add_context_menu(app, w, t))
        except Exception:
            pass

        col += 1
        if col >= cols:
            col = 0
            row += 1

def run_tool(tool_path):
    """运行指定的工具：脚本使用 Python，其他文件使用系统默认程序打开（Windows: os.startfile）"""
    try:
        ext = os.path.splitext(tool_path)[1].lower()
        if ext == '.py':
            import sys
            result = subprocess.run([sys.executable, tool_path],
                                    capture_output=True,
                                    text=True,
                                    check=True)
            print(f"工具运行成功: {result.stdout}")
        else:
            if os.name == 'nt':
                os.startfile(tool_path)
            else:
                subprocess.Popen(['xdg-open', tool_path])
    except subprocess.CalledProcessError as e:
        print(f"工具运行失败: {e.stderr}")
        tk.messagebox.showerror("错误", f"工具运行失败:\n{e.stderr}")
    except Exception as e:
        print(f"运行工具时发生错误: {str(e)}")
        tk.messagebox.showerror("错误", f"运行工具时发生错误:\n{str(e)}")