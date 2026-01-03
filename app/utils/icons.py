# File: ToolBox/app/utils/icons.py
def get_icon_for_filetype(file_type, extension):
    """根据文件类型获取图标符号"""
    icon_map = {
        '压缩包': '📦',
        '可执行文件': '⚙️',
        '脚本文件': '📜',
        '注册表': '🔧',
        '快捷方式': '🔗',
        '文档': '📄',
        '其他': '📎'
    }
    
    special_icons = {
        '.zip': '🗜️',
        '.rar': '🗜️',
        '.7z': '🗜️',
        '.pdf': '📕',
        '.doc': '📘',
        '.xls': '📗',
        '.ppt': '📙',
        '.jpg': '🖼️',
        '.png': '🖼️',
        '.mp3': '🎵',
        '.mp4': '🎬'
    }
    
    if extension in special_icons:
        return special_icons[extension]
    
    return icon_map.get(file_type, '📎')