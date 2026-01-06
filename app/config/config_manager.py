# File: ToolBox/app/config/config_manager.py

import os
import configparser
from pathlib import Path

class ConfigManager:
    def __init__(self):
        # 修改配置文件路径为应用目录下
        self.config_file = Path(__file__).parent.parent.parent / 'ToolBox.ini'
        self.config = configparser.ConfigParser()
        
        if os.path.exists(self.config_file):
            self.config.read(str(self.config_file), encoding='utf-8')
            # 检查配置是否完整，如果缺少必要的部分则补充
            self.ensure_config_complete()
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
    
    def ensure_config_complete(self):
        """确保配置文件包含所有必要的部分"""
        needs_save = False
        
        # 检查General部分是否完整
        general_defaults = {
            'window_width': '1200',
            'window_height': '800',
            'auto_record': '1',
            'scan_interval': '30',
            'enable_subcategories': '1',
            'show_subcategories': '1',
            'notify_new_tools': '1',
            'auto_create_folders': '1',
            'show_welcome_on_startup': '1',
            'display_mode': 'grid'
        }
        
        if not self.config.has_section('General'):
            self.config.add_section('General')
            needs_save = True
        
        for key, default_value in general_defaults.items():
            if not self.config.has_option('General', key):
                self.config.set('General', key, default_value)
                needs_save = True
        
        # 检查Categories部分是否有count值
        if not self.config.has_section('Categories'):
            self.config.add_section('Categories')
            self.config['Categories']['count'] = '0'
            needs_save = True
        elif not self.config.has_option('Categories', 'count'):
            # 如果Categories节存在但没有count，说明是旧配置，使用默认值
            self.config['Categories']['count'] = '0'
            needs_save = True
        elif self.config.get('Categories', 'count') == '0':
            # 如果count为0，保持为0，不设置默认分类
            pass
        
        # 检查Subcategories部分
        if not self.config.has_section('Subcategories'):
            self.config.add_section('Subcategories')
            needs_save = True
            
        # 检查ToolInfo部分
        if not self.config.has_section('ToolInfo'):
            self.config.add_section('ToolInfo')
            needs_save = True
            
        if needs_save:
            self.save_config()
    
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
            'show_welcome_on_startup': '1',
            'display_mode': 'grid'
        }
        
        self.config.add_section('Categories')
        self.config['Categories']['count'] = '0'  # 修改为0，不创建默认分类
    
        self.config.add_section('Subcategories')
        
        self.config.add_section('ToolInfo')  # 新增：用于保存工具自定义标题和备注
        
        self.save_config()
        
        # 创建Storage主目录，但不创建默认分类子目录
        self.create_default_directories()
    
    def create_default_directories(self):
        """创建Storage主目录和分类子目录"""
        # 修改为应用目录下的Storage目录
        toolbox_dir = Path(__file__).parent.parent.parent / "Storage"
        toolbox_dir.mkdir(exist_ok=True)
        
        # 不再创建默认分类目录，保持空目录
        # 之前的代码是创建4个默认分类，现在删除这部分
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"保存配置文件失败: {e}")