# File: ToolBox/app/ui/dialogs.py

from tkinter import Toplevel, Label, Button, Entry, Listbox, Scrollbar, Frame, messagebox, StringVar
from tkinter import ttk
from pathlib import Path
import shutil

def show_category_settings(app):
    """显示分类设置窗口"""
    settings_window = Toplevel(app.root)
    settings_window.title("分类设置")
    settings_window.geometry("850x620")
    settings_window.resizable(True, True)
    settings_window.transient(app.root)
    settings_window.grab_set()

    main_frame = Frame(settings_window)
    main_frame.pack(fill="both", expand=True, padx=15, pady=15)

    Label(main_frame, text="分类设置（添加分类将自动创建文件夹）", font=("Microsoft YaHei", 16, "bold")).pack(pady=(0, 20))

    paned = ttk.Panedwindow(main_frame, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # 左侧：主分类
    left_frame = Frame(paned, relief="sunken", bd=1)
    paned.add(left_frame, weight=1)

    Label(left_frame, text="主分类", font=("Microsoft YaHei", 12, "bold")).pack(pady=(10, 5))

    cat_list_frame = Frame(left_frame)
    cat_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    cat_scroll = Scrollbar(cat_list_frame)
    cat_listbox = Listbox(cat_list_frame, yscrollcommand=cat_scroll.set, exportselection=False)
    cat_scroll.config(command=cat_listbox.yview)
    cat_scroll.pack(side="right", fill="y")
    cat_listbox.pack(side="left", fill="both", expand=True)

    cat_btn_frame = Frame(left_frame)
    cat_btn_frame.pack(pady=10)

    # 使用应用目录下的 Storage，避免与当前工作目录不一致导致刷新失败
    toolbox_dir = app.get_app_dir() / "Storage"

    def simple_input(title, default=""):
        """弹出输入框获取字符串"""
        input_win = Toplevel(settings_window)
        input_win.title(title)
        input_win.geometry("350x180")
        input_win.transient(settings_window)
        input_win.grab_set()

        Label(input_win, text=title, font=("Microsoft YaHei", 11)).pack(pady=20)

        var = StringVar(value=default)
        entry = Entry(input_win, textvariable=var, width=40, font=("Microsoft YaHei", 11))
        entry.pack(pady=10)
        entry.focus()
        entry.select_range(0, 'end')

        result = [None]
        def ok():
            result[0] = var.get().strip()
            input_win.destroy()

        Button(input_win, text="确定", width=10, command=ok).pack(pady=10)
        input_win.bind("<Return>", lambda e: ok())
        input_win.wait_window()
        return result[0]

    def create_folder_if_needed(name):
        folder = toolbox_dir / name
        if not folder.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建文件夹 {folder}\n{e}")

    def add_main_category():
        name = simple_input("新增主分类名称")
        if not name:
            return
        count = int(app.config['Categories'].get('count', '0')) + 1
        app.config['Categories'][str(count)] = name
        app.config['Categories']['count'] = str(count)
        app.config_manager.save_config()
        
        create_folder_if_needed(name)
        
        refresh_main_categories()
        # 立即刷新左侧树，以便新增分类实时可见
        try:
            app.refresh_category_tree()
        except Exception:
            pass
        messagebox.showinfo("成功", f"主分类 '{name}' 已添加\n文件夹已自动创建")

    def rename_main_category():
        sel = cat_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个主分类")
            return
        idx = sel[0] + 1
        old_name = app.config['Categories'].get(str(idx), "")
        new_name = simple_input(f"重命名 '{old_name}' 为", old_name)
        if not new_name or new_name == old_name:
            return
        
        old_folder = toolbox_dir / old_name
        new_folder = toolbox_dir / new_name
        
        if old_folder.exists():
            try:
                old_folder.rename(new_folder)
            except Exception as e:
                messagebox.showerror("错误", f"无法重命名文件夹\n{e}")
                return
        
        app.config['Categories'][str(idx)] = new_name
        app.config_manager.save_config()
        refresh_main_categories()
        refresh_subcategories(idx)
        # 立即刷新左侧树，反映重命名
        try:
            app.refresh_category_tree()
        except Exception:
            pass
        messagebox.showinfo("成功", f"主分类已重命名为 '{new_name}'\n文件夹已重命名")

    def delete_main_category():
        sel = cat_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个主分类")
            return
        idx = sel[0] + 1
        name = app.config['Categories'].get(str(idx), "")
        folder = toolbox_dir / name
        
        delete_folder = False
        if folder.exists():
            if messagebox.askyesno("删除文件夹", f"是否同时删除文件夹 '{name}' 及其所有内容？\n（此操作不可恢复！）"):
                delete_folder = True
        
        if messagebox.askyesno("确认删除", f"确定删除主分类 '{name}'？\n所有二级分类也将被删除"):
            count = int(app.config['Categories'].get('count', '0'))
            for i in range(idx, count):
                app.config['Categories'][str(i)] = app.config['Categories'].get(str(i+1), "")
            app.config['Categories'].pop(str(count), None)
            app.config['Categories']['count'] = str(count - 1)

            sub_keys = [k for k in app.config['Subcategories'] if k.startswith(f"{idx}_")]
            for k in sub_keys:
                app.config['Subcategories'].pop(k, None)

            app.config_manager.save_config()

            if delete_folder and folder.exists():
                try:
                    shutil.rmtree(folder)
                except Exception as e:
                    messagebox.showerror("错误", f"删除文件夹失败\n{e}")

            refresh_main_categories()
            sub_listbox.delete(0, "end")
            # 立即刷新左侧树，反映删除主分类
            try:
                app.refresh_category_tree()
            except Exception:
                pass
            messagebox.showinfo("成功", f"主分类 '{name}' 已删除")

    Button(cat_btn_frame, text="添加主分类", width=12, command=add_main_category).grid(row=0, column=0, padx=5)
    Button(cat_btn_frame, text="重命名", width=12, command=rename_main_category).grid(row=0, column=1, padx=5)
    Button(cat_btn_frame, text="删除", width=12, bg="#e74c3c", fg="white", command=delete_main_category).grid(row=0, column=2, padx=5)

    # 右侧：二级分类
    right_frame = Frame(paned, relief="sunken", bd=1)
    paned.add(right_frame, weight=1)

    Label(right_frame, text="二级分类（选中主分类后显示）", font=("Microsoft YaHei", 12, "bold")).pack(pady=(10, 5))

    sub_list_frame = Frame(right_frame)
    sub_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    sub_scroll = Scrollbar(sub_list_frame)
    sub_listbox = Listbox(sub_list_frame, yscrollcommand=sub_scroll.set, exportselection=False)
    sub_scroll.config(command=sub_listbox.yview)
    sub_scroll.pack(side="right", fill="y")
    sub_listbox.pack(side="left", fill="both", expand=True)

    sub_btn_frame = Frame(right_frame)
    sub_btn_frame.pack(pady=10)

    def add_subcategory():
        sel = cat_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个主分类")
            return
        cat_idx = sel[0] + 1
        cat_name = app.config['Categories'].get(str(cat_idx), "")
        name = simple_input("新增二级分类名称")
        if not name:
            return
        
        # 创建子文件夹
        sub_folder = toolbox_dir / cat_name / name
        try:
            sub_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法创建子文件夹\n{e}")
            return
        
        sub_count = len([k for k in app.config['Subcategories'] if k.startswith(f"{cat_idx}_")]) + 1
        key = f"{cat_idx}_{sub_count}"
        app.config['Subcategories'][key] = name
        app.config_manager.save_config()
        refresh_subcategories(cat_idx)
        # 立即刷新左侧树，反映新增子分类
        try:
            app.refresh_category_tree()
        except Exception:
            pass
        messagebox.showinfo("成功", f"二级分类 '{name}' 已添加\n文件夹已自动创建")

    def rename_subcategory():
        sel = sub_listbox.curselection()
        cat_sel = cat_listbox.curselection()
        if not sel or not cat_sel:
            messagebox.showwarning("提示", "请先选择一个二级分类")
            return
        cat_idx = cat_sel[0] + 1
        sub_idx = sel[0] + 1
        key = f"{cat_idx}_{sub_idx}"
        old_name = app.config['Subcategories'].get(key, "")
        new_name = simple_input(f"重命名 '{old_name}' 为", old_name)
        if not new_name or new_name == old_name:
            return

        cat_name = app.config['Categories'].get(str(cat_idx), "")
        old_sub_folder = toolbox_dir / cat_name / old_name
        new_sub_folder = toolbox_dir / cat_name / new_name

        if old_sub_folder.exists():
            try:
                old_sub_folder.rename(new_sub_folder)
            except Exception as e:
                messagebox.showerror("错误", f"无法重命名子文件夹\n{e}")
                return

        app.config['Subcategories'][key] = new_name
        app.config_manager.save_config()
        refresh_subcategories(cat_idx)
        # 立即刷新左侧树，反映子分类重命名
        try:
            app.refresh_category_tree()
        except Exception:
            pass
        messagebox.showinfo("成功", f"二级分类已重命名为 '{new_name}'\n子文件夹已重命名")
    def delete_subcategory():
        sel = sub_listbox.curselection()
        cat_sel = cat_listbox.curselection()
        if not sel or not cat_sel:
            messagebox.showwarning("提示", "请先选择一个二级分类")
            return
        cat_idx = cat_sel[0] + 1
        sub_idx = sel[0] + 1
        key = f"{cat_idx}_{sub_idx}"
        name = app.config['Subcategories'].get(key, "")
        cat_name = app.config['Categories'].get(str(cat_idx), "")
        sub_folder = toolbox_dir / cat_name / name
        
        delete_folder = False
        if sub_folder.exists():
            if messagebox.askyesno("删除文件夹", f"是否同时删除子文件夹 '{name}' 及其内容？\n（不可恢复）"):
                delete_folder = True
        
        if messagebox.askyesno("确认删除", f"删除二级分类 '{name}'？"):
            app.config['Subcategories'].pop(key, None)
            for i in range(sub_idx + 1, 100):
                old_key = f"{cat_idx}_{i}"
                if old_key in app.config['Subcategories']:
                    new_key = f"{cat_idx}_{i-1}"
                    app.config['Subcategories'][new_key] = app.config['Subcategories'].pop(old_key)
                else:
                    break
            app.config_manager.save_config()
            
            if delete_folder and sub_folder.exists():
                try:
                    shutil.rmtree(sub_folder)
                except Exception as e:
                    messagebox.showerror("错误", f"删除子文件夹失败\n{e}")
            
            refresh_subcategories(cat_idx)
            # 立即刷新左侧树，反映删除
            try:
                app.refresh_category_tree()
            except Exception:
                pass
            messagebox.showinfo("成功", f"二级分类 '{name}' 已删除")

    Button(sub_btn_frame, text="添加二级分类", width=14, command=add_subcategory).grid(row=0, column=0, padx=5)
    Button(sub_btn_frame, text="重命名", width=14, command=rename_subcategory).grid(row=0, column=1, padx=5)
    Button(sub_btn_frame, text="删除", width=14, bg="#e74c3c", fg="white", command=delete_subcategory).grid(row=0, column=2, padx=5)

    def refresh_main_categories():
        cat_listbox.delete(0, "end")
        count = int(app.config['Categories'].get('count', '0'))
        for i in range(1, count + 1):
            name = app.config['Categories'].get(str(i), f"分类{i}")
            cat_listbox.insert("end", name)

    def refresh_subcategories(cat_idx):
        sub_listbox.delete(0, "end")
        subs = []
        for k in app.config['Subcategories']:
            if k.startswith(f"{cat_idx}_"):
                try:
                    num = int(k.split("_")[1])
                    subs.append((num, app.config['Subcategories'][k]))
                except Exception as exc:
                    print(f"读取二级分类编号失败: {k} ({exc})")
                    continue
        subs.sort(key=lambda x: x[0])
        for _, name in subs:
            sub_listbox.insert("end", name)

    def on_cat_select(event):
        sel = cat_listbox.curselection()
        if sel:
            refresh_subcategories(sel[0] + 1)

    cat_listbox.bind("<<ListboxSelect>>", on_cat_select)

    refresh_main_categories()

    original_count = app.config['Categories'].get('count', '0')

    def on_close():
        if app.config['Categories'].get('count', '0') != original_count:
            app.refresh_category_tree()
            if int(app.config['Categories'].get('count', '0')) > 0:
                app.select_category(1)
        settings_window.destroy()

    settings_window.protocol("WM_DELETE_WINDOW", on_close)
    Button(main_frame, text="关闭", width=12, command=on_close).pack(pady=20)

# 在文件末尾添加 show_auto_record_settings 函数
def show_auto_record_settings(app):
    """显示自动记录设置窗口"""
    from tkinter import Toplevel, Label, Frame, Button, Checkbutton, BooleanVar, Entry, StringVar, messagebox
    from pathlib import Path
    
    # 创建设置窗口
    settings_window = Toplevel(app.root)
    settings_window.title("自动记录设置")
    settings_window.geometry("600x500")
    settings_window.transient(app.root)
    settings_window.grab_set()
    
    # 主框架
    main_frame = Frame(settings_window)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    Label(main_frame, text="自动记录设置", font=("Microsoft YaHei", 16, "bold")).pack(pady=(0, 20))
    
    # 设置选项
    settings_frame = Frame(main_frame)
    settings_frame.pack(fill="both", expand=True)
    
    # 各个设置选项
    auto_record_var = BooleanVar()
    enable_subcategories_var = BooleanVar()
    show_subcategories_var = BooleanVar()
    notify_new_tools_var = BooleanVar()
    auto_create_folders_var = BooleanVar()
    show_welcome_var = BooleanVar()
    
    # 从配置中加载当前值
    auto_record_var.set(app.config['General'].get('auto_record', '1') == '1')
    enable_subcategories_var.set(app.config['General'].get('enable_subcategories', '1') == '1')
    show_subcategories_var.set(app.config['General'].get('show_subcategories', '1') == '1')
    notify_new_tools_var.set(app.config['General'].get('notify_new_tools', '1') == '1')
    auto_create_folders_var.set(app.config['General'].get('auto_create_folders', '1') == '1')
    show_welcome_var.set(app.config['General'].get('show_welcome_on_startup', '1') == '1')
    
    # 创建设置项
    Checkbutton(settings_frame, text="启用自动记录", variable=auto_record_var,
                font=("Microsoft YaHei", 10)).pack(anchor='w', pady=5)
    
    Checkbutton(settings_frame, text="启用二级分类", variable=enable_subcategories_var,
                font=("Microsoft YaHei", 10)).pack(anchor='w', pady=5)
    
    Checkbutton(settings_frame, text="显示二级分类", variable=show_subcategories_var,
                font=("Microsoft YaHei", 10)).pack(anchor='w', pady=5)
    
    Checkbutton(settings_frame, text="新工具通知", variable=notify_new_tools_var,
                font=("Microsoft YaHei", 10)).pack(anchor='w', pady=5)
    
    Checkbutton(settings_frame, text="自动创建文件夹", variable=auto_create_folders_var,
                font=("Microsoft YaHei", 10)).pack(anchor='w', pady=5)
    
    Checkbutton(settings_frame, text="启动时显示欢迎页", variable=show_welcome_var,
                font=("Microsoft YaHei", 10)).pack(anchor='w', pady=5)
    
    # 扫描间隔设置
    scan_frame = Frame(settings_frame)
    scan_frame.pack(fill="x", pady=15)
    
    Label(scan_frame, text="扫描间隔（秒）:", font=("Microsoft YaHei", 10)).pack(anchor='w')
    
    scan_interval_var = StringVar()
    scan_interval_var.set(app.config['General'].get('scan_interval', '30'))
    scan_entry = Entry(scan_frame, textvariable=scan_interval_var, width=10, font=("Microsoft YaHei", 10))
    scan_entry.pack(anchor='w', pady=5)
    
    # 保存和关闭按钮
    button_frame = Frame(main_frame)
    button_frame.pack(fill="x", pady=20)
    
    def save_settings():
        # 更新配置
        app.config['General']['auto_record'] = '1' if auto_record_var.get() else '0'
        app.config['General']['enable_subcategories'] = '1' if enable_subcategories_var.get() else '0'
        app.config['General']['show_subcategories'] = '1' if show_subcategories_var.get() else '0'
        app.config['General']['notify_new_tools'] = '1' if notify_new_tools_var.get() else '0'
        app.config['General']['auto_create_folders'] = '1' if auto_create_folders_var.get() else '0'
        app.config['General']['show_welcome_on_startup'] = '1' if show_welcome_var.get() else '0'
        app.config['General']['scan_interval'] = scan_interval_var.get()
        
        # 保存配置
        app.config_manager.save_config()
        
        # 应用自动记录状态更改
        if auto_record_var.get():
            if not app.file_monitor.running:
                app.file_monitor.start()
        else:
            if app.file_monitor.running:
                app.file_monitor.stop()
        
        messagebox.showinfo("成功", "设置已保存")
    
    Button(button_frame, text="保存设置", command=save_settings,
           bg="#27ae60", fg="white", font=("Microsoft YaHei", 10)).pack(side='left', padx=5)
    
    Button(button_frame, text="关闭", command=settings_window.destroy,
           bg="#e74c3c", fg="white", font=("Microsoft YaHei", 10)).pack(side='right', padx=5)
