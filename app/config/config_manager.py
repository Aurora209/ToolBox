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
            self.create_default_config()

    def create_default_config(self):
        """创建默认配置文件"""
        self.config = configparser.ConfigParser()

        self.config.add_section('General')
        self.config['General']['window_width'] = '1200'
        self.config['General']['window_height'] = '800'
        self.config['General']['auto_record'] = '1'
        self.config['General']['scan_interval'] = '30'
        self.config['General']['enable_subcategories'] = '1'
        self.config['General']['show_subcategories'] = '1'
        self.config['General']['notify_new_tools'] = '1'
        self.config['General']['auto_create_folders'] = '1'
        self.config['General']['show_welcome_on_startup'] = '1'
        self.config['General']['display_mode'] = 'grid'

        self.config.add_section('Categories')
        self.config['Categories']['count'] = '0'  # 修改为0，不创建默认分类

        self.config.add_section('Subcategories')

        self.config.add_section('ToolInfo')  # 用于保存工具自定义标题和备注
        self.config.add_section('ToolAddedRecord')  # 用于保存工具添加记录（版本/添加时间/备注等）

        self.save_config()
        self.create_default_directories()

    def create_default_directories(self):
        """创建Storage主目录和分类子目录"""
        toolbox_dir = Path(__file__).parent.parent.parent
        storage_dir = toolbox_dir / 'Storage'
        if not storage_dir.exists():
            storage_dir.mkdir(parents=True, exist_ok=True)

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

        # 检查Categories部分
        if not self.config.has_section('Categories'):
            self.config.add_section('Categories')
            self.config['Categories']['count'] = '0'
            needs_save = True
        elif not self.config.has_option('Categories', 'count'):
            self.config['Categories']['count'] = '0'
            needs_save = True

        # 检查Subcategories部分
        if not self.config.has_section('Subcategories'):
            self.config.add_section('Subcategories')
            needs_save = True

        # 检查ToolInfo部分
        if not self.config.has_section('ToolInfo'):
            self.config.add_section('ToolInfo')
            needs_save = True

        # ✅ 新增：检查 ToolAddedRecord
        if not self.config.has_section('ToolAddedRecord'):
            self.config.add_section('ToolAddedRecord')
            needs_save = True

        if needs_save:
            self.save_config()

    def save_config(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
