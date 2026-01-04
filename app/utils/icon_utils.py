# File: ToolBox/app/utils/icon_utils.py

import os
import sys
from pathlib import Path

# Windows 图标提取模块
try:
    import win32ui
    import win32gui
    import win32con
    from win32com.shell import shell, shellcon
except ImportError:
    win32ui = win32gui = win32con = shell = shellcon = None


def get_tool_icon(self, tool_path, tool_name):
    """获取工具图标"""
    tool_dir = Path(tool_path).parent
    tool_stem = Path(tool_path).stem
    
    custom_ico = tool_dir / f"{tool_stem}.ico"
    custom_png = tool_dir / f"{tool_stem}.png"
    if custom_ico.exists():
        return create_icon_photo(self, custom_ico)
    if custom_png.exists():
        return create_icon_photo(self, custom_png)
    
    if Path(tool_path).suffix.lower() == '.exe':
        icon = extract_exe_icon(self, tool_path)
        if icon:
            return icon
    
    ext = Path(tool_path).suffix.lower()
    from .icons import get_icon_for_filetype
    file_type = get_file_type_category(ext)
    return get_icon_for_filetype(file_type, ext)


def create_icon_photo(self, icon_path):
    """创建图标照片对象"""
    if not hasattr(self, 'icon_cache'):
        self.icon_cache = {}
    
    key = str(icon_path)
    if key in self.icon_cache:
        return self.icon_cache[key]
    
    try:
        from PIL import Image, ImageTk
        img = Image.open(icon_path)
        img = img.resize((48, 48), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.icon_cache[key] = photo
        return photo
    except Exception as e:
        print(f"加载自定义图标失败: {e}")
        return None


def extract_exe_icon(self, exe_path):
    """从exe文件中提取图标"""
    if not all([win32ui, win32gui, shell, shellcon]):
        return None
    
    try:
        from PIL import Image, ImageTk
        
        flags = shellcon.SHGFI_ICON | shellcon.SHGFI_LARGEICON
        shinfo = shell.SHGetFileInfo(exe_path, 0, flags)
        if len(shinfo) >= 4 and shinfo[3] and shinfo[3] != 0:
            hicon = shinfo[3]
            
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, 48, 48)
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            hdc_mem.DrawIcon((0, 0), hicon)
            
            bmp_info = hbmp.GetInfo()
            bmp_str = hbmp.GetBitmapBits(True)
            img = Image.frombuffer('RGBA', (bmp_info['bmWidth'], bmp_info['bmHeight']), bmp_str, 'raw', 'BGRA', 0, 1)
            
            win32gui.DestroyIcon(hicon)
            hdc_mem.DeleteDC()
            hdc.DeleteDC()
            
            photo = ImageTk.PhotoImage(img.resize((48, 48), Image.LANCZOS))
            return photo
    except Exception as e:
        print(f"提取 exe 图标失败: {e}")
    
    return None


def get_file_type_category(ext):
    """根据文件扩展名获取文件类型分类"""
    ext = ext.lower()
    if ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}:
        return "压缩包"
    if ext in {'.exe', '.msi', '.com'}:
        return "可执行文件"
    if ext in {'.bat', '.cmd', '.ps1', '.vbs', '.py', '.sh'}:
        return "脚本文件"
    if ext == '.reg':
        return "注册表"
    if ext == '.lnk':
        return "快捷方式"
    if ext in {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.md', '.html'}:
        return "文档"
    return "其他"