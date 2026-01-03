# File: ToolBox/app/config/config_manager.py

import os
import configparser

class ConfigManager:
    def __init__(self):
        self.config_file = 'ToolBox.ini'
        self.config = configparser.ConfigParser()
        
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self.create_empty_config()
        
        # 确保所有必要节存在
        if not self.config.has_section('General'):
            self.config.add_section('General')
        if not self.config.has_section('Categories'):
            self.config.add_section('Categories')
            self.config['Categories']['count'] = '0'
        if not self.config.has_section('Subcategories'):
            self.config.add_section('Subcategories')
        if not self.config.has_section('ToolInfo'):  # 确保 ToolInfo 节存在
            self.config.add_section('ToolInfo')
    
    def create_empty_config(self):
        """创建空的默认配置（首次运行时使用）"""
        self.config.add_section('General')
        self.config['General'] = {
            'window_width': '1200',
            'window_height': '800',
            'auto_record': '1',
            'scan_interval': '30',
            'enable_subcategories': '1',
            'show_subcategories': '1',
            'notify_new_tools': '1',
            'auto_create_folders': '1',
            'show_welcome_on_startup': '1'
        }
        
        self.config.add_section('Categories')
        self.config['Categories']['count'] = '0'
        
        self.config.add_section('Subcategories')
        
        self.config.add_section('ToolInfo')  # 新增：用于保存工具自定义标题和备注
        
        self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"保存配置文件失败: {e}")