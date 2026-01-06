# File: ToolBox/app/utils/size_utils.py
def format_size(size):
    """格式化文件大小"""
    # Assume implementation from original code, e.g.
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024**3:
        return f"{size / 1024**2:.2f} MB"
    else:
        return f"{size / 1024**3:.2f} GB"