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


def get_tool_icon(self, tool_path, tool_name, size=48):
    """获取工具图标，支持指定大小（px）。优先自定义图标 -> exe 内置图标 -> 按类型的 emoji/占位图。"""
    tool_dir = Path(tool_path).parent
    tool_stem = Path(tool_path).stem
    
    custom_ico = tool_dir / f"{tool_stem}.ico"
    custom_png = tool_dir / f"{tool_stem}.png"
    if custom_ico.exists():
        return create_icon_photo(self, custom_ico, size=size)
    if custom_png.exists():
        return create_icon_photo(self, custom_png, size=size)
    
    if Path(tool_path).suffix.lower() == '.exe':
        icon = extract_exe_icon(self, tool_path, size=size)
        if icon:
            return icon
    
    ext = Path(tool_path).suffix.lower()
    from .icons import get_icon_for_filetype
    file_type = get_file_type_category(ext)

    # 尝试使用 emoji/占位图（若 Pillow 可用则渲染为图片）
    fallback = get_icon_for_filetype(file_type, ext)
    if isinstance(fallback, str):
        try:
            from PIL import Image, ImageTk, ImageDraw, ImageFont
            img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            font_size = max(12, int(size * 0.45))
            try:
                font = ImageFont.truetype("seguiemj.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            w, h = draw.textsize(fallback, font=font)
            draw.text(((size - w) / 2, (size - h) / 2), fallback, font=font, fill=(0, 0, 0, 255))
            photo = ImageTk.PhotoImage(img)
            if not hasattr(self, 'icon_cache'):
                self.icon_cache = {}
            key = f"emoji:{file_type}:{size}"
            self.icon_cache[key] = photo
            return photo
        except Exception:
            # Pillow 不可用或渲染失败，返回 None 由调用端回退到文本或其他显示方式
            return None
    else:
        return create_icon_photo(self, fallback, size=size)


def create_icon_photo(self, icon_path, size=48):
    """创建图标照片对象并缓存。支持指定大小。"""
    if not hasattr(self, 'icon_cache'):
        self.icon_cache = {}
    
    key = f"{str(icon_path)}:{size}"
    if key in self.icon_cache:
        return self.icon_cache[key]
    
    try:
        from PIL import Image, ImageTk
        img = Image.open(icon_path)
        img = img.convert('RGBA')
        img = img.resize((int(size), int(size)), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.icon_cache[key] = photo
        return photo
    except Exception as e:
        print(f"加载自定义图标失败: {e}")
        return None


def extract_exe_icon(self, exe_path, size=48):
    """从exe文件中提取图标并返回 PhotoImage，支持指定大小（px）。需要 pywin32 与 Pillow。"""
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
            hbmp.CreateCompatibleBitmap(hdc, int(size), int(size))
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            # DrawIconEx 等高级绘制可能不存在于某些绑定，使用 DrawIcon 作为回退
            try:
                hdc_mem.DrawIcon((0, 0), hicon)
            except Exception:
                # 尝试用 DrawIconEx
                try:
                    win32gui.DrawIconEx(hdc_mem.GetHandleOutput(), 0, 0, hicon, int(size), int(size), 0, None, win32con.DI_NORMAL)
                except Exception:
                    pass
            bmp_info = hbmp.GetInfo()
            bmp_str = hbmp.GetBitmapBits(True)
            img = Image.frombuffer('RGBA', (bmp_info['bmWidth'], bmp_info['bmHeight']), bmp_str, 'raw', 'BGRA', 0, 1)
            
            try:
                win32gui.DestroyIcon(hicon)
            except Exception:
                pass
            hdc_mem.DeleteDC()
            hdc.DeleteDC()
            
            photo = ImageTk.PhotoImage(img.resize((int(size), int(size)), Image.LANCZOS))
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