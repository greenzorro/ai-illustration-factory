'''
File: child_book_f_fix.py
Project: green
Created: 2025-04-24 02:56:21
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 从UPSCALE_OUTPUT_DIR目录中复制指定前缀的文件到FIX_OUTPUT_DIR目录
'''

import os
import sys
import csv
import shutil

current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(current_dir))

from child_book_utils import *

def copy_files_by_prefix():
    """根据CSV文件中的文件名前缀复制文件
    
    从FIX_CSV_PATH指定的CSV文件中读取file name列作为文件名前缀，
    复制UPSCALE_OUTPUT_DIR目录中所有匹配这些前缀的文件到FIX_OUTPUT_DIR目录
    """
    # 确保输出目录存在
    os.makedirs(FIX_OUTPUT_DIR, exist_ok=True)
    
    # 读取CSV文件获取文件名前缀列表
    prefixes = []
    try:
        with open(FIX_CSV_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'file name' in row and row['file name']:
                    prefixes.append(row['file name'].strip())
    except Exception as e:
        print(f"读取CSV文件失败: {e}")
        return
    
    if not prefixes:
        print(f"CSV文件中没有找到有效的文件名前缀")
        return
    
    print(f"从CSV文件中找到 {len(prefixes)} 个前缀")
    
    # 获取UPSCALE_OUTPUT_DIR目录中的所有文件
    all_files = []
    for root, _, files in os.walk(UPSCALE_OUTPUT_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.tiff', '.tif')):
                all_files.append(os.path.join(root, file))
    
    if not all_files:
        print(f"在 {UPSCALE_OUTPUT_DIR} 目录下没有找到图片文件")
        return
    
    print(f"在源目录中找到 {len(all_files)} 个图片文件")
    
    # 复制匹配前缀的文件
    copied_count = 0
    for prefix in prefixes:
        matched_files = [f for f in all_files if os.path.basename(f).startswith(prefix)]
        
        if not matched_files:
            print(f"警告: 没有找到前缀为 '{prefix}' 的文件")
            continue
        
        for src_path in matched_files:
            file_name = os.path.basename(src_path)
            dst_path = os.path.join(FIX_OUTPUT_DIR, file_name)
            
            try:
                shutil.copy2(src_path, dst_path)
                copied_count += 1
                print(f"已复制: {file_name}")
            except Exception as e:
                print(f"复制文件 {file_name} 失败: {e}")
    
    print(f"\n处理完成! 已复制 {copied_count} 个文件到 {FIX_OUTPUT_DIR}")

def main():
    """主函数"""
    print("开始复制需要修复的图片...")
    copy_files_by_prefix()

if __name__ == "__main__":
    main() 