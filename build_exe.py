#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将 Shopify 爬虫打包为可执行文件
"""

import subprocess
import sys

def install_pyinstaller():
    """安装 PyInstaller"""
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe():
    """打包为可执行文件"""
    print("正在打包...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", "Shopify商品爬虫",
        "--clean",
        "shopify_scraper.py"
    ]
    
    subprocess.check_call(cmd)
    
    print("\n" + "=" * 50)
    print("打包完成！")
    print("可执行文件位于: dist/Shopify商品爬虫.exe")
    print("=" * 50)

if __name__ == "__main__":
    try:
        install_pyinstaller()
        build_exe()
    except Exception as e:
        print(f"打包失败: {e}")
        input("按回车键退出...")
