import tkinter as tk
from tkinter import ttk
from ..ui.display_manager import display_list_mode  # 修复导入路径

def display_tools_grid(app, tools, category_name, count):
    """显示工具网格（在右侧的 tools_container 中渲染）"""
    # 使用工具容器进行渲染
    if not hasattr(app, 'tools_container') or app.tools_container is None:
        print("错误：app.tools_container 未初始化")
        return

    container = app.tools_container

    # 清除现有内容（仅清理右侧容器）
    for widget in container.winfo_children():
        widget.destroy()

    # 创建标题（放在右侧容器）
    title_frame = tk.Frame(container, bg='white')
    title_frame.pack(fill='x', padx=10, pady=10)

    tk.Label(title_frame, text=f"{category_name} ({count})",
             font=('Microsoft YaHei', 14, 'bold'), bg='white').pack(side='left')

    # 工具显示模式选择
    mode_frame = tk.Frame(container, bg='white')
    mode_frame.pack(fill='x', padx=10, pady=(0, 10))

    tk.Label(mode_frame, text="显示模式:", bg='white').pack(side='left')
    mode_var = tk.StringVar(value=app.display_mode if hasattr(app, 'display_mode') else 'list')
    tk.Radiobutton(mode_frame, text="列表", variable=mode_var, value='list',
                   command=lambda: change_display_mode(app, tools, category_name, count, mode_var)).pack(side='left', padx=(10, 0))
    tk.Radiobutton(mode_frame, text="网格", variable=mode_var, value='grid',
                   command=lambda: change_display_mode(app, tools, category_name, count, mode_var)).pack(side='left', padx=(10, 0))

    # 更新状态和当前显示工具
    try:
        app.current_displayed_tools = tools
        app.tool_count_label.config(text=f"工具数量: {count}")
        app.category_status_label.config(text=category_name)
    except Exception:
        pass

    # 设置 showing_all_tools 标志（如果显示的是“所有工具”）
    app.showing_all_tools = True if category_name == '所有工具' else False

    # 初始显示：根据 app.display_mode 决定使用列表或网格
    try:
        current_mode = getattr(app, 'display_mode', 'list')
        print(f"display_tools_grid: 当前 display_mode={current_mode}")
        if current_mode == 'grid':
            from ..ui.display_manager import display_grid_mode
            display_grid_mode(app, tools, category_name, count)
        else:
            display_list_mode(app, tools, category_name, count)
    except Exception as e:
        print(f"display_tools_grid 渲染出错，回退到列表模式: {e}")
        display_list_mode(app, tools, category_name, count)

def change_display_mode(app, tools, category_name, count, mode_var):
    """切换显示模式（包含调试输出）"""
    try:
        mode = mode_var.get()
        print(f"change_display_mode: mode_var={mode}, 当前 app.display_mode={getattr(app,'display_mode',None)}")
        if mode == 'list':
            display_list_mode(app, tools, category_name, count)
        else:
            # 网格模式：调用 UI 层的网格显示实现
            try:
                from ..ui.display_manager import display_grid_mode
                display_grid_mode(app, tools, category_name, count)
            except Exception as e:
                print(f"切换到网格模式失败: {e}")
                display_list_mode(app, tools, category_name, count)

        # 保存显示模式配置
        try:
            app.display_mode = mode
            if hasattr(app, 'config') and hasattr(app, 'config_manager'):
                app.config['General']['display_mode'] = mode
                app.config_manager.save_config()
                print(f"change_display_mode: 已保存显示模式 {mode}")
        except Exception as e:
            print(f"保存显示模式时出错: {e}")
    except Exception as e:
        print(f"change_display_mode 出现异常: {e}")