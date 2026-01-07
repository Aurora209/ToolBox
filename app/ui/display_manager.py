import tkinter as tk
from tkinter import ttk
import os
from ..utils.tool_manager import run_tool as util_run_tool


def _normalize_key(key: str) -> str:
    """
    统一 key：
    - 分隔符统一为反斜杠
    - 去掉首尾空白
    - Windows 下统一转小写，避免 configparser 把 key 自动 lower 导致查不到
    """
    return (key or "").replace("/", "\\").strip().lower()


def _build_record_index(app):
    """
    将 app.tools_added_record 建立索引：normalize(key) -> record
    兼容：
    - tools_added_record 可能为空 / 未加载
    - config['ToolAddedRecord'] 仍可作为兜底数据源
    """
    idx = {}

    # 1) 优先 app.tools_added_record
    tar = getattr(app, "tools_added_record", None)
    if isinstance(tar, dict) and tar:
        for k, v in tar.items():
            idx[_normalize_key(k)] = v

    # 2) 兜底：直接从 config 解析（防止 tools_added_record 没加载/为空）
    cfg = getattr(app, "config", None)
    if cfg and isinstance(cfg, dict) and "ToolAddedRecord" in cfg:
        section = cfg["ToolAddedRecord"]
        for k in section:
            nk = _normalize_key(k)
            if nk in idx:
                continue
            try:
                parts = str(section[k]).split("|", 5)
                if len(parts) >= 6:
                    idx[nk] = {
                        "name": parts[0],
                        "category": parts[1],
                        "add_time": parts[2],
                        "type": parts[3],
                        "note": parts[4],
                        "version": parts[5],
                    }
            except Exception:
                pass

    return idx


def _lookup_added_record(app, tool_path: str, record_index: dict):
    """
    查找某个 tool_path 的记录：
    - 使用相对 storage_path 的 relpath 作为主 key
    - 再尝试绝对路径 key（兼容旧存法）
    - 全部走 normalize(key) 比较
    """
    tool_path = str(tool_path or "")
    if not tool_path:
        return None

    storage = getattr(app, "storage_path", None)

    candidates = []

    # 1) 相对路径 key（推荐）
    if storage:
        try:
            rel = os.path.relpath(tool_path, storage)
            if not rel.startswith(".."):
                candidates.append(rel)
        except Exception:
            pass

    # 2) 绝对路径 key（兼容旧数据）
    candidates.append(tool_path)

    # 3) 尝试一些分隔符变体
    more = []
    for c in candidates:
        more.append(c.replace("\\", "/"))
        more.append(c.replace("/", "\\"))
    candidates.extend(more)

    for c in candidates:
        rec = record_index.get(_normalize_key(c))
        if rec:
            return rec
    return None


def display_list_mode(app, tools, category_name, count):
    """列表模式：显示 序号/名称/分类/版本/添加时间/类型/备注（修复版本/添加时间查不到）"""

    container = getattr(app, "tools_container", app.main_frame)

    # 清空
    for w in container.winfo_children():
        w.destroy()

    # 标题栏
    header = ttk.Frame(container)
    header.pack(fill="x", padx=6, pady=(6, 0))
    ttk.Label(header, text=f"{category_name} （{count}）", font=("Microsoft YaHei", 10, "bold")).pack(side="left")

    # 预先建立记录索引（关键）
    record_index = _build_record_index(app)

    # Treeview
    columns = ("idx", "name", "category", "version", "add_time", "type", "note")
    tree = ttk.Treeview(container, columns=columns, show="headings")

    tree.heading("idx", text="序号")
    tree.heading("name", text="名称")
    tree.heading("category", text="分类")
    tree.heading("version", text="版本")
    tree.heading("add_time", text="添加时间")
    tree.heading("type", text="类型")
    tree.heading("note", text="备注")

    tree.column("idx", width=50, anchor="center")
    tree.column("name", width=260, anchor="w")
    tree.column("category", width=160, anchor="w")
    tree.column("version", width=110, anchor="center")
    tree.column("add_time", width=160, anchor="center")
    tree.column("type", width=100, anchor="center")
    tree.column("note", width=260, anchor="w")

    tree.pack(fill="both", expand=True, padx=6, pady=6)

    # 插入数据（版本/时间来自 ToolAddedRecord）
    for i, tool in enumerate(tools, start=1):
        path = tool.get("path", "")
        rec = _lookup_added_record(app, path, record_index) or {}

        version = rec.get("version", "") or tool.get("version", "")
        add_time = rec.get("add_time", "") or tool.get("add_time", "")
        note = rec.get("note", "") or tool.get("note", "")
        typ = rec.get("type", "") or tool.get("type", "")
        category = rec.get("category", "") or tool.get("category", "")

        tree.insert(
            "",
            "end",
            values=(
                i,
                tool.get("name", ""),
                category,
                version,
                add_time,
                typ,
                note,
            ),
        )

    # 双击运行
    def on_double_click(_event):
        sel = tree.selection()
        if not sel:
            return
        row_index = tree.index(sel[0])
        if 0 <= row_index < len(tools):
            p = tools[row_index].get("path", "")
            if p:
                util_run_tool(app, p)

    tree.bind("<Double-1>", on_double_click)

    # 右键菜单（如果存在）
    try:
        from .context_menu import show_tool_context_menu
        tree.bind("<Button-3>", lambda e: show_tool_context_menu(app, e, tree, tools))
    except Exception:
        pass


def display_grid_mode(app, tools, category_name, count, cols=4):
    """图标模式：紧凑占位 + 可滚动（保持你当前可正常显示图标的逻辑）"""

    container = getattr(app, "tools_container", app.main_frame)

    # 清空
    for w in container.winfo_children():
        w.destroy()

    # 标题栏
    header = ttk.Frame(container)
    header.pack(fill="x", padx=6, pady=(6, 0))
    ttk.Label(header, text=f"{category_name} （{count}）", font=("Microsoft YaHei", 10, "bold")).pack(side="left")

    # 图标大小
    icon_size = 48
    try:
        icon_size = int(app.config["General"].get("icon_size", "48"))
    except Exception:
        icon_size = 48

    size_var = tk.DoubleVar(value=float(icon_size))

    def on_size_change(val):
        try:
            size = int(float(val))
            size = max(24, min(96, size))
            app.config["General"]["icon_size"] = str(size)
            try:
                app.config_manager.save_config()
            except Exception:
                pass
            app.display_grid_mode(tools, category_name, count)
        except Exception:
            pass

    ttk.Label(header, text="图标大小:").pack(side="right", padx=(6, 0))
    ttk.Scale(header, from_=24, to=96, orient="horizontal", variable=size_var, command=on_size_change).pack(side="right")

    # Canvas + Scroll
    outer = ttk.Frame(container)
    outer.pack(fill="both", expand=True, padx=6, pady=6)

    canvas = tk.Canvas(outer, bg="white", highlightthickness=0)
    vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)

    vbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    grid_frame = tk.Frame(canvas, bg="white")
    canvas.create_window((0, 0), window=grid_frame, anchor="nw")

    def _update_scrollregion(_evt=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    grid_frame.bind("<Configure>", _update_scrollregion)

    def _on_mousewheel(event):
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # item 占位（紧凑）
    item_w = max(110, int(icon_size) + 56)
    item_h = max(100, int(icon_size) + 52)

    # 自动列数
    try:
        container.update_idletasks()
        avail_w = container.winfo_width()
        if avail_w and avail_w > 200:
            cols_use = max(1, (avail_w - 24) // (item_w + 10))
        else:
            cols_use = int(cols) if cols else 4
    except Exception:
        cols_use = int(cols) if cols else 4

    for i in range(cols_use):
        grid_frame.grid_columnconfigure(i, weight=0)

    row, col = 0, 0
    for tool in tools:
        path = tool.get("path", "")
        name = tool.get("name", "")

        item = tk.Frame(
            grid_frame,
            bg="white",
            width=item_w,
            height=item_h,
            highlightthickness=1,
            highlightbackground="#dcdcdc",
        )
        item.grid(row=row, column=col, padx=6, pady=6, sticky="n")
        item.grid_propagate(False)

        # icon
        icon = None
        try:
            icon = app.get_tool_icon(path, name, size=icon_size)
        except Exception:
            icon = None

        if icon and not isinstance(icon, str):
            lab = tk.Label(item, image=icon, bg="white")
            lab.image = icon
            lab.pack(pady=(8, 2))
        else:
            tk.Label(
                item,
                text="？" if not isinstance(icon, str) else icon,
                bg="white",
                font=("Segoe UI Emoji", max(12, int(icon_size * 0.55))),
                fg="#444",
            ).pack(pady=(10, 2))

        tk.Label(item, text=name, bg="white", wraplength=item_w - 10, justify="center",
                 font=("Microsoft YaHei", 9)).pack(padx=6, pady=(0, 6))

        # 双击运行
        item.bind("<Double-1>", lambda e, p=path: util_run_tool(app, p))
        for child in item.winfo_children():
            child.bind("<Double-1>", lambda e, p=path: util_run_tool(app, p))

        # 右键菜单
        try:
            from .context_menu import add_context_menu
            add_context_menu(app, item, tool)
            for child in item.winfo_children():
                add_context_menu(app, child, tool)
        except Exception:
            pass

        col += 1
        if col >= cols_use:
            col = 0
            row += 1
