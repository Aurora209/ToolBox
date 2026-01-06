# File: ToolBox/app/utils/file_utils.py
import os
from pathlib import Path

def get_file_version_info(file_path):
    """获取文件的版本信息（仅限Windows）。

    优先使用 pywin32 的 win32api 获取；若不可用则回退到 PowerShell 调用（兼容没有 pywin32 的环境）。
    返回类似 {'file_version': '1.2.3.4', 'product_version': '1.2.3.4', ...}，若无法读取返回 None。
    """
    if not Path(file_path).exists() or os.name != 'nt':
        return None

    # 优先尝试 win32api
    try:
        import win32api
        info = win32api.GetFileVersionInfo(str(file_path), '\\')
        version_info = {}
        # 解析常见的字段（不同 Windows 版本与工具可能有不同的键）
        if 'FileVersion' in info:
            version_info['file_version'] = info['FileVersion']
        if 'ProductVersion' in info:
            version_info['product_version'] = info['ProductVersion']
        if 'ProductName' in info:
            version_info['product_name'] = info['ProductName']
        if 'FileDescription' in info:
            version_info['description'] = info['FileDescription']
        return version_info if version_info else None
    except Exception as exc:
        print(f"读取版本信息失败(win32api): {exc}")

    # 回退：使用 powershell 获取版本信息（如果系统支持）
    try:
        import subprocess, json, shlex
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-Item -LiteralPath '{str(file_path).replace("'","''")}').VersionInfo | ConvertTo-Json -Compress"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        if proc.returncode == 0 and proc.stdout:
            try:
                data = json.loads(proc.stdout)
                version_info = {}
                if isinstance(data, dict):
                    if data.get('FileVersion'):
                        version_info['file_version'] = data.get('FileVersion')
                    if data.get('ProductVersion'):
                        version_info['product_version'] = data.get('ProductVersion')
                    if data.get('ProductName'):
                        version_info['product_name'] = data.get('ProductName')
                    if data.get('FileDescription'):
                        version_info['description'] = data.get('FileDescription')
                return version_info if version_info else None
            except Exception as exc:
                print(f"解析版本信息失败(powershell): {exc}")
                return None
    except Exception as exc:
        print(f"读取版本信息失败(powershell): {exc}")

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
    except Exception as exc:
        print(f"限制日志文件大小失败: {exc}")
