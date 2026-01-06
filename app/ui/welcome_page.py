# File: ToolBox/app/ui/welcome_page.py

from tkinter import Label, Frame


def show_welcome_page(app):
    """显示欢迎页面"""
    for widget in app.tools_container.winfo_children():
        widget.destroy()
    
    welcome_text = """欢迎使用便携软件管理箱！

🎉 感谢您选择本工具箱，这是一个专为便携软件设计的轻量级管理器。

【快速开始指南】
• 点击左侧下方的 "分类设置" 按钮管理分类
• 支持一级分类和二级分类（在设置中直接添加）
• 将便携程序放入对应文件夹，即可在此处双击运行

【核心功能】
✓ 树状分类导航（支持一级展开二级）
✓ 双击工具直接运行（显示真实图标）
✓ 支持自定义工具图标（右键 → 修改图标）
✓ 支持图标模式与列表模式切换
✓ 列表模式显示序号与添加时间
✓ 自动记录工具添加信息（含版本号）
✓ 压缩包管理（双击解压）
✓ 全局搜索与类型过滤
✓ 右键菜单支持修改标题、添加备注、修改图标

祝您使用愉快！如果需要帮助，可随时查看 "自动记录设置" 或 "分类设置"。

—— 便携软件管理箱 v1.0"""

    frame = Frame(app.tools_container, bg='white')
    frame.pack(fill='both', expand=True)
    
    Label(frame, text=welcome_text,
          font=("Microsoft YaHei", 12), fg='#2c3e50', bg='white',
          justify='left', padx=60, pady=60, wraplength=700).pack(expand=True)