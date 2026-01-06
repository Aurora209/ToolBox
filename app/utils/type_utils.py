# File: ToolBox/app/utils/type_utils.py

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