# File: ToolBox/main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import tkinter.messagebox as messagebox
import traceback

from app.app import ToolBox

def main():
    try:
        # Windows DPI设置
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass
        
        app = ToolBox()
        
    except Exception as e:
        messagebox.showerror("启动错误", f"程序启动失败:\n{str(e)}")
        with open('error.log', 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())

if __name__ == "__main__":
    main()