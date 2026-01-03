# File: ToolBox/app/utils/file_utils.py
import os
from pathlib import Path

def get_file_version_info(file_path):
    """获取文件的版本信息（仅限Windows）"""
    if not Path(file_path).exists() or os.name != 'nt':
        return None
    
    try:
        import win32api
        info = win32api.GetFileVersionInfo(str(file_path), '\\')
        
        version_info = {}
        if 'FileVersion' in info:
            version_info['file_version'] = info['FileVersion']
        if 'ProductVersion' in info:
            version_info['product_version'] = info['ProductVersion']
        if 'ProductName' in info:
            version_info['product_name'] = info['ProductName']
        if 'FileDescription' in info:
            version_info['description'] = info['FileDescription']
        
        return version_info if version_info else None
    except:
        return None

def limit_log_file_size(log_file, max_lines=1000):
    """限制日志文件大小"""
    try:
        if Path(log_file).exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
    except:
        pass