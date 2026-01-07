# File: ToolBox/app/ui/display_mode_manager.py

from tkinter import Frame, Label, Radiobutton, StringVar


def add_display_mode_switch(app):
    """在右侧工具容器上方添加显示模式切换（图标/列表）"""
    # tools_container 必须已创建
    if not hasattr(app, "tools_container") or app.tools_container is None:
        return

    parent = app.tools_container.master

    # 防止重复创建
    if hasattr(app, "_display_mode_switch_frame") and app._display_mode_switch_frame:
        try:
            app._display_mode_switch_frame.destroy()
        except Exception:
            pass

    switch_frame = Frame(parent, bg="#f0f0f0")
    switch_frame.pack(fill="x", before=app.tools_container, pady=(10, 5))
    app._display_mode_switch_frame = switch_frame

    Label(
        switch_frame,
        text="显示模式：",
        font=("Microsoft YaHei", 10),
        bg="#f0f0f0",
    ).pack(side="left", padx=10)

    # 绑定到 app，供 switch_display_mode 使用
    var_mode = StringVar(value=getattr(app, "display_mode", "grid"))
    app.var_display_mode = var_mode

    Radiobutton(
        switch_frame,
        text="图标模式",
        variable=var_mode,
        value="grid",
        font=("Microsoft YaHei", 10),
        bg="#f0f0f0",
        command=lambda: switch_display_mode(app),
    ).pack(side="left", padx=(5, 0))

    Radiobutton(
        switch_frame,
        text="列表模式",
        variable=var_mode,
        value="list",
        font=("Microsoft YaHei", 10),
        bg="#f0f0f0",
        command=lambda: switch_display_mode(app),
    ).pack(side="left", padx=(5, 0))


def switch_display_mode(app):
    """切换显示模式：保持当前视图（分类/全部工具）不变，仅重绘显示方式"""
    try:
        # 兼容：变量不存在时直接返回
        if not hasattr(app, "var_display_mode") or app.var_display_mode is None:
            return

        new_mode = app.var_display_mode.get()
        cur_mode = getattr(app, "display_mode", "grid")

        # 没变化就不刷新
        if new_mode == cur_mode:
            return

        # 更新模式 & 保存配置
        app.display_mode = new_mode
        try:
            if hasattr(app, "config") and hasattr(app, "config_manager"):
                if "General" not in app.config:
                    app.config["General"] = {}
                app.config["General"]["display_mode"] = new_mode
                app.config_manager.save_config()
        except Exception:
            # 保存失败不影响界面刷新
            pass

        # 关键修复：如果当前是“全部工具”视图，不能 refresh_tools（会因树未选中而刷空）
        if getattr(app, "showing_all_tools", False):
            if hasattr(app, "load_and_display_all_tools"):
                app.load_and_display_all_tools()
            else:
                # 兜底：若没有该方法，再用 refresh_tools
                if hasattr(app, "refresh_tools"):
                    app.refresh_tools()
        else:
            if hasattr(app, "refresh_tools"):
                app.refresh_tools()

    except Exception as e:
        print(f"switch_display_mode 出现异常: {e}")
