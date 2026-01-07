# File: ToolBox/app/utils/icon_utils.py

import os
import sys
import base64
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
    """获取工具图标，支持指定大小（px）。优先自定义图标 -> exe 内置图标 -> 按类型 emoji 图标"""
    tool_dir = Path(tool_path).parent
    tool_stem = Path(tool_path).stem

    # 自定义图标：同名 .ico / .png
    custom_ico = tool_dir / f"{tool_stem}.ico"
    custom_png = tool_dir / f"{tool_stem}.png"
    if custom_ico.exists():
        return create_icon_photo(self, custom_ico, size=size)
    if custom_png.exists():
        return create_icon_photo(self, custom_png, size=size)

    # exe：提取原生图标
    if Path(tool_path).suffix.lower() == '.exe':
        icon = extract_exe_icon(self, tool_path, size=size)
        if icon:
            return icon

    # fallback：按类型 emoji（若 Pillow 可用则渲染成 PhotoImage）
    ext = Path(tool_path).suffix.lower()
    from .icons import get_icon_for_filetype
    file_type = get_file_type_category(ext)
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
            try:
                bbox = draw.textbbox((0, 0), fallback, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except Exception:
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
    """加载图标文件（png/ico）并返回 Tk PhotoImage（带缓存）"""
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
    """从 exe 文件中提取 Windows 原生图标并返回 PhotoImage。

    修复点：
    - 旧实现用 CreateCompatibleBitmap，位深不保证 32bpp，读取 BGRA 时经常失败
    - 新实现强制使用 CreateDIBSection(32bpp) + DrawIconEx，稳定得到 BGRA
    - 优先用 ctypes + SHGetFileInfoW（不依赖 pywin32）
    - 若 Pillow 可用：返回带 alpha 的 PhotoImage；否则返回 PPM PhotoImage（无 alpha）
    """
    if os.name != 'nt':
        return None

    try:
        import ctypes
        from ctypes import wintypes
        from tkinter import PhotoImage

        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        SHGFI_ICON = 0x000000100
        SHGFI_LARGEICON = 0x000000000
        SHGFI_SMALLICON = 0x000000001
        flags = SHGFI_ICON | (SHGFI_SMALLICON if int(size) <= 32 else SHGFI_LARGEICON)

        class SHFILEINFO(ctypes.Structure):
            _fields_ = [
                ('hIcon', wintypes.HICON),
                ('iIcon', ctypes.c_int),
                ('dwAttributes', wintypes.DWORD),
                ('szDisplayName', wintypes.WCHAR * 260),
                ('szTypeName', wintypes.WCHAR * 80),
            ]

        shinfo = SHFILEINFO()
        ret = shell32.SHGetFileInfoW(
            wintypes.LPCWSTR(str(exe_path)),
            0,
            ctypes.byref(shinfo),
            ctypes.sizeof(shinfo),
            flags
        )
        if ret == 0 or not shinfo.hIcon:
            return None

        hicon = shinfo.hIcon

        width = int(size)
        height = int(size)

        BI_RGB = 0
        DIB_RGB_COLORS = 0

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', ctypes.c_long),
                ('biHeight', ctypes.c_long),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(hdc_mem, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        if not hbmp:
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            user32.DestroyIcon(hicon)
            return None

        h_old = gdi32.SelectObject(hdc_mem, hbmp)

        buf_len = width * height * 4
        ctypes.memset(bits, 0, buf_len)

        DI_NORMAL = 0x0003
        user32.DrawIconEx(hdc_mem, 0, 0, hicon, width, height, 0, None, DI_NORMAL)

        raw = ctypes.string_at(bits, buf_len)

        gdi32.SelectObject(hdc_mem, h_old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        user32.DestroyIcon(hicon)

        # 优先 Pillow 保留 alpha
        try:
            from PIL import Image, ImageTk  # type: ignore
            img = Image.frombuffer('RGBA', (width, height), raw, 'raw', 'BGRA', 0, 1)
            return ImageTk.PhotoImage(img)
        except Exception:
            # 无 Pillow：转 PPM（无 alpha）
            rgb = bytearray(width * height * 3)
            j = 0
            for i in range(0, len(raw), 4):
                b = raw[i]
                g = raw[i + 1]
                r = raw[i + 2]
                rgb[j] = r
                rgb[j + 1] = g
                rgb[j + 2] = b
                j += 3

            header = f'P6 {width} {height} 255\n'.encode('ascii')
            ppm = header + bytes(rgb)
            b64 = base64.b64encode(ppm)
            return PhotoImage(data=b64, format='PPM')

    except Exception as e:
        print(f'提取 exe 图标失败(ctypes): {e}')
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
