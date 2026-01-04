import zipfile
import tarfile
from shutil import copyfile
from tkinter import filedialog, messagebox
from pathlib import Path

try:
    import rarfile
except ImportError:
    rarfile = None

try:
    import py7zr
except ImportError:
    py7zr = None


def extract_archive(app, path):
    extract_to = filedialog.askdirectory(title="选择解压目录")
    if not extract_to:
        return
    
    ext = Path(path).suffix.lower()
    try:
        if ext == '.zip':
            with zipfile.ZipFile(path, 'r') as zf:
                zf.extractall(extract_to)
        elif ext == '.rar' and rarfile:
            with rarfile.RarFile(path, 'r') as rf:
                rf.extractall(extract_to)
        elif ext == '.7z' and py7zr:
            with py7zr.SevenZipFile(path, 'r') as szf:
                szf.extractall(extract_to)
        else:
            with tarfile.open(path, 'r:*') as tf:
                tf.extractall(extract_to)
        
        messagebox.showinfo("成功", f"解压完成到：\n{extract_to}")
        app.refresh_tools()
    except Exception as e:
        messagebox.showerror("解压失败", str(e))