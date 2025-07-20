'''
File: child_book_3_ppi.py
Project: green
Created: 2025-04-07 10:00:26
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 
'''

import os
import sys
from PIL import Image

current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(current_dir))

from child_book_utils import *

# 常量定义
MAX_SHORT_SIDE = 1772  # 短边最大值
MIN_WIDTH = 1772  # 纵向图片的最小宽度

def process_images():
    """
    处理下载目录中 PPI_SRC_DIR 文件夹及其子文件夹里的所有图片：
    1. 使用 scale_image 限制图片短边
    2. 设置 PPI 为 450
    3. 在输出和临时目录中保持原始子目录结构
    """
    # 源目录和目标目录
    src_folder = PPI_SRC_DIR
    output_folder = PPI_OUTPUT_DIR
    temp_folder = PPI_TEMP_DIR
    
    # 确保输出目录和临时目录存在
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(temp_folder, exist_ok=True)
    
    # 支持的图片格式
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.avif')
    
    print(f"开始处理目录: {src_folder}")
    
    # 递归遍历源目录中的所有文件和子目录
    for root, dirs, files in os.walk(src_folder):
        # 计算当前目录相对于源目录的路径
        relative_dir = os.path.relpath(root, src_folder)
        
        # 在输出和临时目录中创建对应的子目录
        current_output_dir = os.path.join(output_folder, relative_dir) if relative_dir != '.' else output_folder
        current_temp_dir = os.path.join(temp_folder, relative_dir) if relative_dir != '.' else temp_folder
        os.makedirs(current_output_dir, exist_ok=True)
        os.makedirs(current_temp_dir, exist_ok=True)
            
        for filename in files:
            if filename.lower().endswith(image_extensions):
                # 构建完整的文件路径
                src_path = os.path.join(root, filename)
                
                # 临时文件路径
                temp_path = os.path.join(current_temp_dir, filename)
                
                # 最终输出文件路径
                dst_path = os.path.join(current_output_dir, filename)
                
                try:
                    print(f"处理图片: {os.path.join(relative_dir, filename) if relative_dir != '.' else filename}")
                    
                    # 步骤1: 使用scale_image限制图片短边
                    if MAX_SHORT_SIDE is not None:
                        scale_image(src_path, temp_path, MAX_SHORT_SIDE, MIN_WIDTH, mode=2)
                        process_path = temp_path
                    else:
                        process_path = src_path
                    
                    # 步骤2: 设置PPI为450
                    with Image.open(process_path) as img:
                        # 如果是透明背景转为不透明，先将Alpha通道删除
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        set_image_ppi(process_path, dst_path, target_ppi=450)
                    
                    print(f"成功处理: {os.path.join(relative_dir, filename) if relative_dir != '.' else filename} -> {os.path.join(os.path.basename(output_folder), relative_dir, filename) if relative_dir != '.' else os.path.join(os.path.basename(output_folder), filename)}")
                    
                except Exception as e:
                    print(f"处理 {os.path.join(relative_dir, filename) if relative_dir != '.' else filename} 时出错: {e}")
    
    print(f"所有图片处理完成。输出目录: {output_folder}")

if __name__ == "__main__":
    process_images()
