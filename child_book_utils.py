'''
File: child_book_utils.py
Project: child-book
Created: 2025-03-28 11:42:40
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 
'''

import os
import sys
import requests
import urllib3
import time
import json
import shutil
import csv
from datetime import datetime
from PIL import Image
from runcomfy_utils import *

# 全局常量定义
# 选择计费方式：'hobby' 或 'pro'
RUNCOMFY_BILLING_TYPE = 'hobby'

# 目录常量定义
HOME = os.path.expanduser('~')
PATH_DOWNLOADS = os.path.join(HOME, 'Downloads')
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(LOCAL_PATH, '程序工作流')

# 图像生成相关目录
GEN_RETRY_CSV_PATH = os.path.join(BASE_PATH, "AI插画_图片表_Retry.csv")
GEN_EXPORT_CSV_PATH = os.path.join(BASE_PATH, "AI插画_图片表_Gen.csv")
GEN_OUTPUT_RETRY_DIR = os.path.join(BASE_PATH, 'child-book-retry')
GEN_OUTPUT_DEFAULT_DIR = os.path.join(BASE_PATH, 'child-book-gen')

# 图像放大相关目录
UPSCALE_SRC_DIR = os.path.join(BASE_PATH, "child-book-gen")
UPSCALE_OUTPUT_DIR = os.path.join(BASE_PATH, 'child-book-upscaled')

# 局部修复相关目录
GEN_INPAINT_CSV_PATH = os.path.join(BASE_PATH, "AI插画_图片表_Inpaint.csv")
INPAINT_CROP_SRC_DIR = os.path.join(BASE_PATH, "child-book-upscaled")
INPAINT_CROP_OUTPUT_DIR = os.path.join(BASE_PATH, "child-book-cropped")
INPAINT_PASTE_SRC_DIR = os.path.join(BASE_PATH, "src")
INPAINT_PASTE_OUTPUT_DIR = os.path.join(BASE_PATH, "child-book-upscaled")

# 图像修复相关目录
FIX_CSV_PATH = os.path.join(BASE_PATH, "AI插画_图片表_Fix.csv")
FIX_OUTPUT_DIR = os.path.join(BASE_PATH, 'child-book-fix')

# Photoshop处理相关目录
PS_CSV_PATH = os.path.join(BASE_PATH, "AI插画_图片表_Ps.csv")
PS_OUTPUT_DIR = os.path.join(BASE_PATH, 'child-book-ps')

# 图像按风格整理相关目录
ORGANIZE_UPSCALED_SRC = os.path.join(BASE_PATH, 'child-book-upscaled')

# PPI处理相关目录
PPI_SRC_DIR = os.path.join(BASE_PATH, 'child-book-upscaled')
PPI_OUTPUT_DIR = os.path.join(BASE_PATH, 'child-book-ppi')
PPI_TEMP_DIR = os.path.join(BASE_PATH, 'temp')

# 图像按项目整理相关目录
ORGANIZE_PROJECT_SRC = os.path.join(BASE_PATH, 'src')
ORGANIZE_PROJECT_OUTPUT = os.path.join(BASE_PATH, 'final')

def scale_image(src_path, dst_path, max_size, min_width, mode=1):
    """等比缩放图片，根据模式选择缩放长边或短边

    :param str src_path: 源图片路径
    :param str dst_path: 目标图片路径
    :param int max_size: 最大尺寸值
    :param int min_width: 长图的最小宽度（仅对纵向图片生效）
    :param int mode: 模式（1-长边缩放到最大值 2-短边缩放到最大值）
    """
    image = Image.open(src_path)
    width, height = image.size
    
    # 确定长边和短边
    long_side = max(width, height)
    short_side = min(width, height)
    
    # 根据不同模式计算缩放比例
    if mode == 1:
        # 模式1：长边缩放到最大值
        if long_side > max_size:
            ratio = max_size / long_side
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # 仅对纵向图片检查最小宽度
            if height > width and new_width < min_width:
                # 调整缩放后的宽度和高度（保持原比例）
                new_width = min_width
                new_height = int(min_width / width * height)
                
            # 缩放图片
            image = image.resize((new_width, new_height))
    
    elif mode == 2:
        # 模式2：短边缩放到最大值
        if short_side > max_size:
            ratio = max_size / short_side
            new_width = int(width * ratio)
            new_height = int(height * ratio)
        else:
            # 如果短边小于最大值，则放大到最大值
            ratio = max_size / short_side
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
        # 仅对纵向图片检查最小宽度
        if height > width and new_width < min_width:
            # 调整缩放后的宽度和高度（保持原比例）
            new_width = min_width
            new_height = int(min_width / width * height)
            
        # 缩放图片
        image = image.resize((new_width, new_height))

    # 输出文件
    image.save(dst_path)

def calculate_tile_coordinates(src_path: str, tile_width: int, tile_height: int, x_tile_count: int, y_tile_count: int, x_tile_num: int, y_tile_num: int) -> tuple[int, int]:
    """
    计算在给定网格布局下，特定瓦片的左上角坐标。

    将源图片想象成一个大致的网格，由 x_tile_count * y_tile_count 个瓦片组成，
    每个瓦片的尺寸为 tile_width * tile_height。
    此函数计算第 (x_tile_num, y_tile_num) 个瓦片（基于1的索引）的左上角像素坐标 (x, y)。

    瓦片的分布是均匀的：
    - 第一个水平瓦片(x_tile_num=1)的左边缘与图像左边缘对齐 (x=0)。
    - 最后一个水平瓦片(x_tile_num=x_tile_count)的*左*边缘应使得其*右*边缘与图像右边缘对齐 (x=img_width-tile_width)。
    - 第一个垂直瓦片(y_tile_num=1)的上边缘与图像上边缘对齐 (y=0)。
    - 最后一个垂直瓦片(y_tile_num=y_tile_count)的*上*边缘应使得其*下*边缘与图像下边缘对齐 (y=img_height-tile_height)。
    中间瓦片的起始点均匀分布在这些边界之间。允许瓦片重叠或未覆盖整个图像。

    :param str src_path: 源图片路径。
    :param int tile_width: 每个瓦片的宽度。
    :param int tile_height: 每个瓦片的高度。
    :param int x_tile_count: 水平方向上的瓦片总数（必须 >= 2）。
    :param int y_tile_count: 垂直方向上的瓦片总数（必须 >= 2）。
    :param int x_tile_num: 所需瓦片的水平索引（1 到 x_tile_count）。
    :param int y_tile_num: 所需瓦片的垂直索引（1 到 y_tile_count）。
    :raises ValueError: 如果 tile_count < 2 或 tile_num 超出范围。
    :raises FileNotFoundError: 如果源图片未找到。
    :raises IOError: 如果打开图片时出错。
    :return: 一个包含计算出的 (x_coordinate, y_coordinate) 的元组。
    :rtype: tuple[int, int]
    """
    if x_tile_count < 2 or y_tile_count < 2:
        raise ValueError("x_tile_count 和 y_tile_count 必须大于等于 2")

    if not (1 <= x_tile_num <= x_tile_count):
        raise ValueError(f"x_tile_num ({x_tile_num}) 必须在 1 和 {x_tile_count} 之间")

    if not (1 <= y_tile_num <= y_tile_count):
        raise ValueError(f"y_tile_num ({y_tile_num}) 必须在 1 和 {y_tile_count} 之间")

    try:
        # 确保在使用 Image 对象后关闭它
        with Image.open(src_path) as image:
            img_width, img_height = image.size
    except FileNotFoundError:
        raise FileNotFoundError(f"源图片未找到: {src_path}")
    except Exception as e:
        raise IOError(f"打开图片时出错 {src_path}: {e}")

    # 如果图像尺寸小于瓦片尺寸，无法进行有效分布，或者计算会出错
    if img_width < tile_width or img_height < tile_height:
         raise ValueError(f"图像尺寸 ({img_width}x{img_height}) 小于瓦片尺寸 ({tile_width}x{tile_height})")

    # 计算水平方向上相邻瓦片起点的间距
    # (img_width - tile_width) 是第一个瓦片起点(0)到最后一个瓦片起点(img_width - tile_width)的总距离
    # 这个总距离被 (x_tile_count - 1) 个间隔平分
    # 确保除数不为零 (虽然前面已检查 x_tile_count >= 2，这里更健壮)
    spacing_x = (img_width - tile_width) / (x_tile_count - 1) if x_tile_count > 1 else 0

    # 计算垂直方向上相邻瓦片起点的间距
    spacing_y = (img_height - tile_height) / (y_tile_count - 1) if y_tile_count > 1 else 0

    # 计算目标瓦片左上角的坐标 (使用基于0的索引进行计算，所以用 tile_num - 1)
    # 使用 round() 进行四舍五入，以获得更居中的分布感觉
    x_coordinate = round((x_tile_num - 1) * spacing_x)
    y_coordinate = round((y_tile_num - 1) * spacing_y)

    # 确保坐标不会因为浮点数精度问题或round导致最后一个瓦片稍微超出边界
    # 最后一个瓦片的起点不应超过 img_width - tile_width 或 img_height - tile_height
    if x_tile_num == x_tile_count:
        x_coordinate = img_width - tile_width
    if y_tile_num == y_tile_count:
        y_coordinate = img_height - tile_height

    # 同样确保第一个瓦片的起点正好是0
    if x_tile_num == 1:
        x_coordinate = 0
    if y_tile_num == 1:
        y_coordinate = 0

    return x_coordinate, y_coordinate

def paste_image(src_path1: str, src_path2: str, dst_path: str, x_coordinate: int, y_coordinate: int):
    """
    将一张图片 (src1) 粘贴到另一张图片 (src2) 的指定坐标上。

    如果 src1 超出 src2 的边界，超出部分将被裁剪。
    如果 src1 具有透明度，将使用 alpha 混合粘贴。

    :param str src_path1: 要粘贴的顶层图片路径。
    :param str src_path2: 背景图片路径。
    :param str dst_path: 保存结果图片的路径。
    :param int x_coordinate: src1 左上角在 src2 上的 x 坐标 (可以为负)。
    :param int y_coordinate: src1 左上角在 src2 上的 y 坐标 (可以为负)。
    :raises FileNotFoundError: 如果任一源文件未找到。
    :raises IOError: 如果打开或处理图片时出错。
    """
    try:
        # 使用 with 语句确保文件被正确关闭
        with Image.open(src_path1) as img1, Image.open(src_path2) as img2:
            w1, h1 = img1.size
            w2, h2 = img2.size
            mode1 = img1.mode

            # 检查顶层图片 img1 是否有 alpha 通道
            has_alpha1 = mode1 in ('RGBA', 'LA') or (mode1 == 'P' and 'transparency' in img1.info)

            # 准备背景图片作为基础
            # 如果顶层图片有 alpha，确保基础图片是 RGBA 模式以进行混合
            if has_alpha1:
                result_image = img2.convert('RGBA') if img2.mode != 'RGBA' else img2.copy()
            else:
                # 如果顶层图片不透明，直接复制背景（Pillow 的 paste 可以处理模式）
                result_image = img2.copy()

            # --- 计算裁剪和粘贴区域 --- 

            # 1. 计算 img1 需要被裁剪的区域 (crop box on img1)
            #    这部分的坐标是相对于 img1 左上角的 (0,0)
            crop_x_start = max(0, -x_coordinate)
            crop_y_start = max(0, -y_coordinate)
            #    结束坐标：考虑 img1 尺寸以及它在 img2 上的右/下边界
            crop_x_end = min(w1, w2 - x_coordinate)
            crop_y_end = min(h1, h2 - y_coordinate)

            # 2. 计算实际需要裁剪的宽度和高度
            crop_width = crop_x_end - crop_x_start
            crop_height = crop_y_end - crop_y_start

            # 3. 计算裁剪出的区域应该粘贴到 result_image 的哪个位置
            #    这部分的坐标是相对于 result_image 左上角的 (0,0)
            paste_x = max(0, x_coordinate)
            paste_y = max(0, y_coordinate)

            # --- 执行裁剪和粘贴 --- 

            # 仅当存在有效的重叠区域时执行操作
            if crop_width > 0 and crop_height > 0:
                # 从 img1 裁剪出需要粘贴的部分
                region_to_paste = img1.crop((crop_x_start, crop_y_start, crop_x_end, crop_y_end))

                # 准备蒙版 (mask) - 仅当顶层图片有 alpha 时需要
                mask = None
                if has_alpha1:
                    # 确保裁剪出的区域也是 RGBA 模式，然后提取 alpha 通道作为蒙版
                    # L mode P mode RGBA mode
                    if region_to_paste.mode not in ('RGBA', 'LA'):
                        region_to_paste = region_to_paste.convert('RGBA')
                    mask = region_to_paste.split()[-1] # 获取 alpha 通道

                # 将裁剪出的区域粘贴到背景图片上
                result_image.paste(region_to_paste, (paste_x, paste_y), mask)

            # 保存最终结果
            # Pillow 会根据文件扩展名选择格式，通常能正确处理模式
            # 对于不支持 alpha 的格式（如 JPG），透明度会丢失（通常变为白色或黑色）
            result_image.save(dst_path)

    except FileNotFoundError as e:
        # 提供更明确的错误信息，指出哪个文件未找到
        missing_file = src_path1 if not os.path.exists(src_path1) else src_path2
        raise FileNotFoundError(f"源文件未找到: {missing_file}") from e
    except Exception as e:
        raise IOError(f"处理图片 '{src_path1}' 或 '{src_path2}' 时出错: {e}") from e

def runcomfy_watercolor(prompt, instance_url, batch_size=1, save_dir=PATH_DOWNLOADS, output_name=None, max_retries=3):
    """使用RunComfy工作流生成水彩风格图片
    
    参数:
    - prompt: 图片生成的文本描述
    - instance_url: ComfyUI实例URL
    - batch_size: 一次生成的图片数量
    - save_dir: 生成图片保存的目录
    - output_name: 输出文件名前缀，如果不指定则使用时间戳
    - max_retries: 最大重试次数
    
    返回:
    - 生成的图片文件路径列表
    """
    # 加载工作流JSON
    workflow_path = os.path.join(os.path.dirname(__file__), "runcomfy_watercolor_api.json")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    # 生成随机种子
    new_seed = generate_seed()
    print(f"使用随机种子: {new_seed}")
    
    # 更新工作流中的种子和batch_size
    workflow["202"]["inputs"]["seed"] = new_seed
    workflow["101"]["inputs"]["batch_size"] = batch_size  # 同时更新EmptyLatentSizePicker的batch_size
    workflow["140"]["inputs"]["batch_size"] = batch_size  # 同时更新EmptySD3LatentImage的batch_size
    
    # 配置输入
    inputs = {
        "177": {  # 177是工作流JSON中CLIPTextEncode节点的ID
            "type": "text",
            "text": prompt
        }
    }
    
    print("开始生成图片...")
    print(f"批量大小: {batch_size}")
    print(f"使用实例: {instance_url}")
    
    # 外层重试逻辑
    for attempt in range(max_retries):
        try:
            # 确保输出目录存在
            os.makedirs(save_dir, exist_ok=True)
            # 如果没有指定output_name，则使用时间戳
            if output_name is None:
                output_name = f"watercolor_{int(time.time())}"
            
            print(f"将结果保存到: {save_dir}")
            print(f"输出文件名前缀: {output_name}")
            
            # 执行工作流
            result = runcomfy_workflow(
                workflow_json=workflow,
                inputs=inputs,
                instance_url=instance_url,
                verify_ssl=True,
                max_retries=2  # 指定内部重试次数
            )
            
            if not result or 'outputs' not in result:
                print("警告: 工作流执行成功但没有返回输出数据")
                if attempt < max_retries - 1:
                    print(f"将在 5 秒后重试 (尝试 {attempt+2}/{max_retries})...")
                    time.sleep(5)
                    continue
                return None
                
            # 下载输出文件
            saved_files = runcomfy_download_outputs(
                outputs=result['outputs'],
                instance_url=instance_url,
                save_dir=save_dir,
                output_name=output_name,
                verify_ssl=True
            )
            
            print(f"生成成功，生成了 {len(saved_files)} 个文件")
            return saved_files  # 返回所有生成的文件路径
            
        except Exception as e:
            print(f"尝试 {attempt+1}/{max_retries} 失败: {str(e)}")
            
            # 记录详细错误信息
            if attempt == max_retries - 1:  # 最后一次尝试
                print("详细错误信息:")
                import traceback
                traceback.print_exc()
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                # 使用指数退避
                wait_time = 5 * (2 ** attempt)  # 5, 10, 20...
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
    
    # 如果所有尝试都失败
    raise Exception(f"在 {max_retries} 次尝试后生成图片失败")

def runcomfy_flat(prompt, instance_url, batch_size=1, save_dir=PATH_DOWNLOADS, output_name=None, max_retries=3):
    """使用RunComfy工作流生成扁平风格图片
    
    参数:
    - prompt: 图片生成的文本描述
    - instance_url: ComfyUI实例URL
    - batch_size: 一次生成的图片数量
    - save_dir: 生成图片保存的目录
    - output_name: 输出文件名前缀，如果不指定则使用时间戳
    - max_retries: 最大重试次数
    
    返回:
    - 生成的图片文件路径列表
    """
    # 加载工作流JSON
    workflow_path = os.path.join(os.path.dirname(__file__), "runcomfy_flat_api.json")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    # 生成随机种子
    new_seed = generate_seed()
    print(f"使用随机种子: {new_seed}")
    
    # 更新工作流中的种子和batch_size
    workflow["202"]["inputs"]["seed"] = new_seed
    workflow["101"]["inputs"]["batch_size"] = batch_size  # 同时更新EmptyLatentSizePicker的batch_size
    workflow["140"]["inputs"]["batch_size"] = batch_size  # 同时更新EmptySD3LatentImage的batch_size
    
    # 配置输入
    inputs = {
        "177": {  # 177是工作流JSON中CLIPTextEncode节点的ID
            "type": "text",
            "text": prompt
        }
    }
    
    print("开始生成图片...")
    print(f"批量大小: {batch_size}")
    print(f"使用实例: {instance_url}")
    
    # 外层重试逻辑
    for attempt in range(max_retries):
        try:
            # 确保输出目录存在
            os.makedirs(save_dir, exist_ok=True)
            # 如果没有指定output_name，则使用时间戳
            if output_name is None:
                output_name = f"flat_{int(time.time())}"
            
            print(f"将结果保存到: {save_dir}")
            print(f"输出文件名前缀: {output_name}")
            
            # 执行工作流
            result = runcomfy_workflow(
                workflow_json=workflow,
                inputs=inputs,
                instance_url=instance_url,
                verify_ssl=True,
                max_retries=2  # 指定内部重试次数
            )
            
            if not result or 'outputs' not in result:
                print("警告: 工作流执行成功但没有返回输出数据")
                if attempt < max_retries - 1:
                    print(f"将在 5 秒后重试 (尝试 {attempt+2}/{max_retries})...")
                    time.sleep(5)
                    continue
                return None
                
            # 下载输出文件
            saved_files = runcomfy_download_outputs(
                outputs=result['outputs'],
                instance_url=instance_url,
                save_dir=save_dir,
                output_name=output_name,
                verify_ssl=True
            )
            
            print(f"生成成功，生成了 {len(saved_files)} 个文件")
            return saved_files  # 返回所有生成的文件路径
            
        except Exception as e:
            print(f"尝试 {attempt+1}/{max_retries} 失败: {str(e)}")
            
            # 记录详细错误信息
            if attempt == max_retries - 1:  # 最后一次尝试
                print("详细错误信息:")
                import traceback
                traceback.print_exc()
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                # 使用指数退避
                wait_time = 5 * (2 ** attempt)  # 5, 10, 20...
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
    
    # 如果所有尝试都失败
    raise Exception(f"在 {max_retries} 次尝试后生成图片失败")

def runcomfy_upscale(image_path, instance_url, save_dir=PATH_DOWNLOADS, max_retries=3):
    """使用RunComfy工作流放大图像
    
    参数:
    - image_path: 需要放大的图像文件路径
    - instance_url: ComfyUI实例URL
    - save_dir: 放大后图像保存的目录
    - max_retries: 最大重试次数
    
    返回:
    - 放大后的图像文件路径
    """
    # 加载工作流JSON
    workflow_path = os.path.join(os.path.dirname(__file__), "runcomfy_upscale_api.json")
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    # 生成随机种子
    new_seed = generate_seed()
    print(f"使用随机种子: {new_seed}")
    
    # 更新工作流中的种子
    workflow["259"]["inputs"]["seed"] = new_seed
    
    # 配置输入
    inputs = {
        "264": {  # 264是工作流JSON中LoadImage节点的ID
            "type": "image",
            "path": image_path
        }
    }
    
    print("开始放大图像处理...")
    print(f"原图路径: {image_path}")
    print(f"使用实例: {instance_url}")
    
    # 外层重试逻辑
    for attempt in range(max_retries):
        try:
            # 确保输出目录存在
            os.makedirs(save_dir, exist_ok=True)
            output_name = os.path.basename(image_path).split('.')[0]
            
            print(f"将结果保存到: {save_dir}")
            print(f"输出文件名前缀: {output_name}")
            
            # 执行工作流
            result = runcomfy_workflow(
                workflow_json=workflow,
                inputs=inputs,
                instance_url=instance_url,
                verify_ssl=True,
                max_retries=2  # 指定内部重试次数
            )
            
            if not result or 'outputs' not in result:
                print("警告: 工作流执行成功但没有返回输出数据")
                if attempt < max_retries - 1:
                    print(f"将在 5 秒后重试 (尝试 {attempt+2}/{max_retries})...")
                    time.sleep(5)
                    continue
                return None
                
            # 下载输出文件
            saved_files = runcomfy_download_outputs(
                outputs=result['outputs'],
                instance_url=instance_url,
                save_dir=save_dir,
                output_name=output_name,
                verify_ssl=True
            )
            
            print(f"放大成功，生成了 {len(saved_files)} 个文件")
            return saved_files[0]  # 只返回第一个文件路径，因为这个工作流只生成一张图片
            
        except Exception as e:
            print(f"尝试 {attempt+1}/{max_retries} 失败: {str(e)}")
            
            # 记录详细错误信息
            if attempt == max_retries - 1:  # 最后一次尝试
                print("详细错误信息:")
                import traceback
                traceback.print_exc()
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                # 使用指数退避
                wait_time = 5 * (2 ** attempt)  # 5, 10, 20...
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
    
    # 如果所有尝试都失败
    raise Exception(f"在 {max_retries} 次尝试后放大图像失败")

def organize_images_by_style():
    """将放大后的图片按风格分类到不同文件夹
    
    将 ORGANIZE_UPSCALED_SRC 目录下的图片按照其原始风格
    分类到同一目录下的 {style} 子目录中。
    风格名称从文件名中提取，位于第1个"-"和第2个"-"之间。
    """
    # 源目录
    src_dir = ORGANIZE_UPSCALED_SRC
    if not os.path.exists(src_dir):
        print(f"错误：源目录不存在: {src_dir}")
        return
        
    # 获取所有图片文件
    image_files = []
    for file in os.listdir(src_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image_files.append(file)
    
    if not image_files:
        print(f"在 {src_dir} 目录下没有找到图片文件")
        return
        
    print(f"\n开始按风格整理图片...")
    print(f"找到 {len(image_files)} 个图片文件")
    
    # 移动文件到对应的风格目录
    moved_count = 0
    for image_file in image_files:
        # 从文件名中提取风格名称
        parts = image_file.split('-')
        if len(parts) < 3:
            print(f"警告：文件名格式不正确，无法提取风格: {image_file}")
            continue
            
        style = parts[1]  # 第1个"-"和第2个"-"之间的内容
        if not style:
            print(f"警告：无法从文件名中提取风格: {image_file}")
            continue
            
        # 创建风格子目录
        style_dir = os.path.join(src_dir, style)
        os.makedirs(style_dir, exist_ok=True)
            
        # 移动文件
        src_path = os.path.join(src_dir, image_file)
        dst_path = os.path.join(style_dir, image_file)
        try:
            shutil.move(src_path, dst_path)
            moved_count += 1
        except Exception as e:
            print(f"移动文件失败 {image_file}: {e}")
    
    print(f"整理完成，成功移动 {moved_count} 个文件到对应的风格目录")

def organize_images_by_project():
    """将 src 目录下的图片按项目分类到 TIFF 目录下的子目录中
    
    源目录: ORGANIZE_PROJECT_SRC
    目标目录: ORGANIZE_PROJECT_OUTPUT
    
    文件名格式示例：1-w-1-女孩桌上画幻想.xxx
    第1个"-"前的数字作为项目目录名
    处理所有子目录中的图片，并在处理完成后删除风格子目录
    """
    # 源目录
    src_dir = ORGANIZE_PROJECT_SRC
    if not os.path.exists(src_dir):
        print(f"错误：源目录不存在: {src_dir}")
        return
    
    # 目标根目录
    tiff_root_dir = ORGANIZE_PROJECT_OUTPUT
    os.makedirs(tiff_root_dir, exist_ok=True)
    
    # 获取所有图片文件（包括子目录）
    image_files = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.tiff', '.tif')):
                image_files.append(os.path.join(root, file))
    
    if not image_files:
        print(f"在 {src_dir} 目录下没有找到图片文件")
        return
    
    print(f"\n开始按类别整理图片...")
    print(f"找到 {len(image_files)} 个图片文件")
    
    # 移动文件到对应的类别目录
    moved_count = 0
    processed_styles = set()  # 记录已处理的风格子目录
    
    for image_path in image_files:
        # 从文件名中提取类别和风格
        filename = os.path.basename(image_path)
        parts = filename.split('-')
        
        if len(parts) < 2:
            print(f"警告：文件名格式不正确，无法提取类别: {filename}")
            continue
        
        project = parts[0]  # 第1个"-"前的内容作为类别
        if not project:
            print(f"警告：无法从文件名中提取类别: {filename}")
            continue
        
        # 创建类别目录
        project_dir = os.path.join(tiff_root_dir, project)
        os.makedirs(project_dir, exist_ok=True)
        
        # 移动文件
        dst_path = os.path.join(project_dir, filename)
        try:
            shutil.move(image_path, dst_path)
            moved_count += 1
            
            # 记录风格子目录，以便后续删除
            style_dir = os.path.dirname(image_path)
            if style_dir != src_dir and style_dir not in processed_styles:
                processed_styles.add(style_dir)
        except Exception as e:
            print(f"移动文件失败 {filename}: {e}")
    
    # 删除风格子目录
    for style_dir in processed_styles:
        try:
            # 确保只删除空目录
            if os.path.exists(style_dir) and not os.listdir(style_dir):
                os.rmdir(style_dir)
                print(f"删除空的风格子目录: {style_dir}")
        except Exception as e:
            print(f"删除风格子目录 {style_dir} 失败: {e}")
    
    print(f"整理完成，成功移动 {moved_count} 个文件到对应的类别目录，并删除风格子目录")

def log_script_execution(script_type, image_count, start_time, end_time, billable_minutes, billing_type, machine_type, machine_price_per_hour, estimated_cost):
    """记录脚本执行日志
    
    参数:
    - script_type: 脚本类型（'gen' 或 'upscale'）
    - image_count: 处理的场景数量
    - start_time: 开始运行时间（datetime对象）
    - end_time: 结束运行时间（datetime对象）
    - billable_minutes: 实际计费时长（分钟，已减去机器启动时间）
    - billing_type: 计费方式（'hobby' 或 'pro'）
    - machine_type: 机器类型
    - machine_price_per_hour: 每小时机器价格
    - estimated_cost: 预估使用成本
    """
    # 日志文件路径
    log_dir = os.path.join(LOCAL_PATH, 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'child-book-run.csv')
    
    # 日志记录时间（当前时间）
    log_time = datetime.now()
    
    # 准备日志数据
    log_data = [
        log_time.strftime('%Y-%m-%d %H:%M:%S'),  # 日志记录时间
        script_type,                             # 脚本类型
        image_count,                             # 场景数量
        start_time.strftime('%Y-%m-%d %H:%M:%S'),# 开始运行时间
        end_time.strftime('%Y-%m-%d %H:%M:%S'),  # 结束运行时间
        f"{billable_minutes:.2f}",               # 实际计费时长（分钟）
        billing_type,                            # 计费方式
        machine_type,                            # 机器类型
        f"{machine_price_per_hour:.2f}",         # 单价
        f"{estimated_cost:.2f}"                  # 使用成本
    ]
    
    # 检查文件是否存在，不存在则创建并写入表头
    file_exists = os.path.exists(log_file_path)
    
    with open(log_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # 如果文件不存在，写入表头
        if not file_exists:
            header = [
                '日志记录时间', '脚本类型', '场景数量', '开始运行时间', '结束运行时间', 
                '计费时长(分钟)', '计费方式', '机器类型', '单价($/小时)', '使用成本($)'
            ]
            csvwriter.writerow(header)
        
        # 写入日志数据
        csvwriter.writerow(log_data)
