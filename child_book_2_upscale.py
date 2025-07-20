'''
File: child_book_2_upscale.py
Project: green
Created: 2025-04-07 10:00:26
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 
'''

import os
import sys
import time
from datetime import datetime

current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(current_dir))

from child_book_utils import *

# 机器类型常量
MACHINE_TYPE = "medium"

# 指定默认保存目录
save_dir = UPSCALE_OUTPUT_DIR
os.makedirs(save_dir, exist_ok=True)

# 主函数
def main():
    # 记录开始时间
    start_time = time.time()
    start_datetime = datetime.now()
    print(f"\n开始运行时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    src_dir = UPSCALE_SRC_DIR
    
    # 获取src目录下的所有图片文件
    image_files = []
    for file in os.listdir(src_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image_files.append(os.path.join(src_dir, file))
    
    if not image_files:
        print(f"在 {src_dir} 目录下没有找到图片文件")
        exit(1)
        
    # 按文件名排序
    image_files.sort()
        
    print(f"找到 {len(image_files)} 个图片文件:")
    for image_file in image_files:
        print(f"- {os.path.basename(image_file)}")
    print()

    # 使用RunComfy工作流放大图片
    try:
        # 获取或创建RunComfy实例
        instance_url = runcomfy_service.get_or_create_instance(
            create_new_instance=True,  # 设置为True将创建新实例
            server_type=MACHINE_TYPE,
            estimated_duration=14400
        )
        print(f"获取到RunComfy实例: {instance_url}")
        
        # 处理每一张图片
        for image_path in image_files:
            base_name_with_ext = os.path.basename(image_path)
            base_name_no_ext = os.path.splitext(base_name_with_ext)[0]
            
            # 检查目标目录中是否已存在以 base_name_no_ext 开头的文件
            found_existing = False
            for existing_file in os.listdir(save_dir):
                if existing_file.startswith(base_name_no_ext):
                    print(f"文件 {base_name_with_ext} 的放大版本 ({existing_file}) 已存在于目标目录，跳过放大。")
                    found_existing = True
                    break
            
            if found_existing:
                continue

            print(f"\n开始处理图片: {base_name_with_ext}")
            try:
                # 使用实例执行放大操作
                upscaled_file = runcomfy_upscale(
                    image_path=image_path, 
                    instance_url=instance_url,
                    save_dir=save_dir
                )
                print(f"放大后的图片已保存至: {upscaled_file}")
            except Exception as e:
                print(f"处理图片 {base_name_with_ext} 失败: {e}")
                continue
        
        # 处理完成后关闭实例
        try:
            runcomfy_service.stop_instance()
            print("\n已关闭RunComfy实例")
        except Exception as e:
            print(f"\n关闭实例失败: {e}")
            
    except Exception as e:
        print(f"处理失败: {e}")
        # 发生错误时也尝试关闭实例
        try:
            runcomfy_service.stop_instance()
            print("\n已关闭RunComfy实例")
        except Exception as e:
            print(f"\n关闭实例失败: {e}")
    
    # 记录结束时间并计算耗时
    end_time = time.time()
    end_datetime = datetime.now()
    duration_minutes = (end_time - start_time) / 60
    
    # 按风格整理放大后的图片
    organize_images_by_style()
    
    # 计算实际计费时间（扣除启动时间）
    billable_minutes = calculate_billable_minutes(duration_minutes)
    
    # 计算机器使用成本
    machine_price_per_hour = RUNCOMFY_MACHINE_PRICES[RUNCOMFY_BILLING_TYPE][MACHINE_TYPE]
    estimated_cost = billable_minutes * (machine_price_per_hour / 60)
    
    print(f"\n开始运行时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束运行时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总运行时间: {duration_minutes:.2f} 分钟")
    print(f"实际计费时间: {billable_minutes:.2f} 分钟")
    print(f"使用机器类型: {MACHINE_TYPE}")
    print(f"计费方式: {RUNCOMFY_BILLING_TYPE}")
    print(f"预估使用成本: ${estimated_cost:.2f}")

    # 记录脚本执行日志
    log_script_execution(
        script_type='upscale',
        image_count=len(image_files),
        start_time=start_datetime,
        end_time=end_datetime,
        billable_minutes=billable_minutes,
        billing_type=RUNCOMFY_BILLING_TYPE,
        machine_type=MACHINE_TYPE,
        machine_price_per_hour=machine_price_per_hour,
        estimated_cost=estimated_cost
    )

if __name__ == "__main__":
    main()
