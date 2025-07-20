'''
File: child_book_m_paste.py
Project: green
Created: 2025-04-07 10:00:26
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 
'''

import os
import sys
import pandas as pd

current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(current_dir))

from child_book_utils import *

# 固定的瓦片网格和尺寸常量
X_TILE_COUNT = 5
Y_TILE_COUNT = 5
TILE_WIDTH = 1024
TILE_HEIGHT = 1024

def find_file_in_subdirs(base_dir, filename_prefix):
    """在基础目录及其子目录中递归查找第一个匹配前缀的文件（尝试常见扩展名）"""
    common_extensions = ['.png', '.jpg', '.jpeg', '.webp']
    # print(f"DEBUG: Searching for files starting with '{filename_prefix}' in {base_dir}") # Debug print
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().startswith(filename_prefix.lower()):
                file_ext = os.path.splitext(f)[1].lower()
                if file_ext in common_extensions:
                    full_path = os.path.join(root, f)
                    if os.path.isfile(full_path):
                        # print(f"DEBUG: Found matching file for prefix '{filename_prefix}': {full_path}") # Debug print
                        return full_path
    # print(f"DEBUG: No file found starting with prefix '{filename_prefix}' in {base_dir}") # Debug print
    return None

# 主函数
def main():
    # 读取 CSV 文件
    try:
        df = pd.read_csv(GEN_INPAINT_CSV_PATH, encoding='utf-8')

        # 检查必需的列
        required_columns = ['file name', 'inpaint x', 'inpaint y']
        if not all(col in df.columns for col in required_columns):
            print(f"错误：CSV 文件 {GEN_INPAINT_CSV_PATH} 缺少必需的列 ({required_columns})")
            return

        # 遍历每一行
        for index, row in df.iterrows():
            base_filename_prefix = row['file name'] # Use as prefix
            inpaint_x = row['inpaint x']
            inpaint_y = row['inpaint y']

            # 1. 在 INPAINT_CROP_SRC_DIR 及其子目录中查找原始放大图 (使用前缀匹配)
            src_path = find_file_in_subdirs(INPAINT_CROP_SRC_DIR, base_filename_prefix)
            if not src_path:
                print(f"警告：在 {INPAINT_CROP_SRC_DIR} 及其子目录中未找到以 '{base_filename_prefix}' 开头的原始放大图（已尝试常见扩展名）")
                continue
            
            # 提取实际找到的原始文件名（带扩展名和无扩展名）
            src_filename_with_ext = os.path.basename(src_path)
            base_filename_no_ext = os.path.splitext(src_filename_with_ext)[0]
            
            # 2. 构建精确的瓦片文件名 (基于找到的原始文件名)
            tile_filename = f"{base_filename_no_ext}_{inpaint_x}_{inpaint_y}.png"
            # 3. 构建瓦片路径 (在 INPAINT_PASTE_SRC_DIR 中查找)
            tile_path = os.path.join(INPAINT_PASTE_SRC_DIR, tile_filename)
            
            # 4. 检查瓦片图片是否存在
            if not os.path.exists(tile_path):
                print(f"警告：修复后的瓦片图片不存在 {tile_path}")
                continue

            try:
                # 5. 计算瓦片坐标（基于找到的原始放大图 src_path）
                x_coordinate, y_coordinate = calculate_tile_coordinates(
                    src_path=src_path,
                    tile_width=TILE_WIDTH,
                    tile_height=TILE_HEIGHT,
                    x_tile_count=X_TILE_COUNT,
                    y_tile_count=Y_TILE_COUNT,
                    x_tile_num=inpaint_x,
                    y_tile_num=inpaint_y
                )

                # 6. 设置目标路径为原始放大图路径，实现覆盖
                dst_path = src_path

                # 7. 将修复后的瓦片图片粘贴回原图
                paste_image(
                    src_path1=tile_path,   # 修复后的瓦片
                    src_path2=src_path,   # 原始放大图作为背景
                    dst_path=dst_path,    # 输出路径 (覆盖原始放大图)
                    x_coordinate=x_coordinate,
                    y_coordinate=y_coordinate
                )

                print(f"成功将 {tile_filename} 粘贴到 {dst_path}") # 更新日志信息

            except Exception as e:
                print(f"处理 {base_filename_prefix} (找到文件: {src_filename_with_ext}) 的瓦片 ({inpaint_x}, {inpaint_y}) 时出错: {e}")

    except FileNotFoundError:
        print(f"错误：未找到 CSV 文件 {GEN_INPAINT_CSV_PATH}")
    except pd.errors.EmptyDataError:
        print(f"错误：CSV 文件 {GEN_INPAINT_CSV_PATH} 为空")
    except Exception as e:
        print(f"处理 CSV 文件时出错: {e}")

if __name__ == "__main__":
    main() 