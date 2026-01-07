import zipfile
import tarfile
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import rarfile
except ImportError:  # pragma: no cover
    rarfile = None

try:
    import py7zr
except ImportError:  # pragma: no cover
    py7zr = None


def _is_within_directory(base_dir: Path, target_path: Path) -> bool:
    """判断 target_path 是否在 base_dir 内（resolve 后防止 .. / symlink 绕过）。"""
    try:
        base = base_dir.resolve()
        target = target_path.resolve()
        return base == target or base in target.parents
    except Exception:
        return False


def _safe_extract_zip(zf: zipfile.ZipFile, extract_to: Path) -> None:
    for member in zf.infolist():
        member_path = extract_to / member.filename
        if not _is_within_directory(extract_to, member_path):
            raise ValueError(f"检测到不安全的压缩条目路径：{member.filename}")
    zf.extractall(extract_to)


def _safe_extract_tar(tf: tarfile.TarFile, extract_to: Path) -> None:
    for member in tf.getmembers():
        member_path = extract_to / member.name
        if not _is_within_directory(extract_to, member_path):
            raise ValueError(f"检测到不安全的压缩条目路径：{member.name}")
    tf.extractall(extract_to)


def _safe_extract_rar(rf, extract_to: Path) -> None:
    for name in rf.namelist():
        member_path = extract_to / name
        if not _is_within_directory(extract_to, member_path):
            raise ValueError(f"检测到不安全的压缩条目路径：{name}")
    rf.extractall(extract_to)


def _safe_extract_7z(szf, extract_to: Path) -> None:
    names = []
    try:
        names = szf.getnames()
    except Exception:
        names = []
    for name in names:
        member_path = extract_to / name
        if not _is_within_directory(extract_to, member_path):
            raise ValueError(f"检测到不安全的压缩条目路径：{name}")
    szf.extractall(extract_to)


def extract_archive(app, archive_path: str):
    """解压压缩包到指定目录，并刷新工具列表。"""
    path = Path(archive_path)
    if not path.exists():
        messagebox.showerror("错误", "压缩包不存在")
        return

    extract_to = filedialog.askdirectory(title="选择解压目录")
    if not extract_to:
        return
    extract_to = Path(extract_to)

    try:
        ext = path.suffix.lower()

        if ext == '.zip':
            with zipfile.ZipFile(path, 'r') as zf:
                _safe_extract_zip(zf, extract_to)
        elif ext == '.rar':
            if not rarfile:
                raise RuntimeError("未安装 rarfile，无法解压 .rar")
            with rarfile.RarFile(path, 'r') as rf:
                _safe_extract_rar(rf, extract_to)
        elif ext == '.7z':
            if not py7zr:
                raise RuntimeError("未安装 py7zr，无法解压 .7z")
            with py7zr.SevenZipFile(path, 'r') as szf:
                _safe_extract_7z(szf, extract_to)
        else:
            with tarfile.open(path, 'r:*') as tf:
                _safe_extract_tar(tf, extract_to)

        messagebox.showinfo("成功", f"解压完成到：\n{extract_to}")
        if hasattr(app, 'refresh_tools'):
            app.refresh_tools()
    except Exception as e:
        messagebox.showerror("解压失败", str(e))
