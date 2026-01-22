#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将爬虫程序打包为Windows可执行文件
需要在 Windows 电脑上运行此脚本
"""

import subprocess
import sys

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe():
    """打包为exe文件"""
    print("正在打包...")
    
    # PyInstaller 参数说明:
    # --onefile: 打包成单个exe文件
    # --console: 显示控制台窗口（爬虫需要显示进度）
    # --name: 指定输出文件名
    # --clean: 清理临时文件
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", "SLP商品爬虫",
        "--clean",
        "slp_scraper_simple.py"
    ]
    
    subprocess.check_call(cmd)
    
    print("\n" + "=" * 50)
    print("打包完成！")
    print("可执行文件位于: dist/SLP商品爬虫.exe")
    print("=" * 50)

if __name__ == "__main__":
    try:
        install_pyinstaller()
        build_exe()
    except Exception as e:
        print(f"打包失败: {e}")
        input("按回车键退出...")
