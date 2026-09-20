"""应用路径工具 - 兼容PyInstaller打包后的可写路径"""

import sys
from pathlib import Path


def app_root() -> Path:
    """应用根目录：开发时为项目目录，打包后为exe所在目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def data_dir() -> Path:
    """数据目录（词缀数据库）"""
    d = app_root() / "data"
    d.mkdir(exist_ok=True)
    return d


def config_dir() -> Path:
    """配置目录"""
    d = app_root() / "config"
    d.mkdir(exist_ok=True)
    return d
