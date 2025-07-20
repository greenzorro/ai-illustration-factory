'''
File: child_book_1_gen.py
Project: green
Created: 2025-04-07 10:00:26
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 使用RunComfy工作流生成不同风格的图片
'''

import os
import sys
import time
from datetime import datetime
import pandas as pd

current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(current_dir))

from child_book_utils import *

# 机器类型常量
MACHINE_TYPE = "medium"

# 生成配置
GEN_CONFIG = {
    'watercolor': {'batch_size': 4},
    'flat': {'batch_size': 2}
}

# 主函数
def main():
    # 记录开始时间
    start_time = time.time()
    start_datetime = datetime.now()
    print(f"\n开始运行时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 确定输入 CSV 和输出目录 
    input_csv_path = None
    output_folder_name = None

    if os.path.exists(GEN_RETRY_CSV_PATH):
        input_csv_path = GEN_RETRY_CSV_PATH
        output_folder_name = 'child-book-retry'
        print(f"找到 Retry CSV: {input_csv_path}")
    elif os.path.exists(GEN_EXPORT_CSV_PATH):
        input_csv_path = GEN_EXPORT_CSV_PATH
        output_folder_name = 'child-book-gen'
        print(f"找到 Gen CSV: {input_csv_path}")
    else:
        print(f"错误：在 {BASE_PATH} 目录下未找到 教辅插图_图片表_Retry.csv 或 教辅插图_图片表_Gen.csv")
        exit(1)
        
    # 定义并创建保存目录 
    save_dir = os.path.join(BASE_PATH, output_folder_name)
    os.makedirs(save_dir, exist_ok=True)
    print(f"图片将保存至: {save_dir}")
    
    # 从 CSV 读取提示词 
    try:
        df = pd.read_csv(input_csv_path, encoding='utf-8')
        # 检查必需的列是否存在
        required_columns = ['file name', 'style', 'final prompt']
        if not all(col in df.columns for col in required_columns):
            print(f"错误: CSV 文件 {input_csv_path} 缺少必需的列 ({required_columns})")
            exit(1)
            
        # 清理数据：移除 final prompt 为空的行
        df.dropna(subset=['final prompt'], inplace=True)
        df = df[df['final prompt'].str.strip() != '']
        
        # 将数据转换为所需的字典列表格式
        prompts = df.apply(
            lambda row: {
                "name": row['file name'],
                "style": row['style'],
                "prompt": row['final prompt']
            },
            axis=1
        ).tolist()

        if not prompts:
            print(f"从 {input_csv_path} 读取到 0 个有效的 prompt。请检查文件内容。")
            exit(1)

        print(f"从 {os.path.basename(input_csv_path)} 加载了 {len(prompts)} 个 prompts.")

    except FileNotFoundError:
        print(f"错误：无法找到文件 {input_csv_path}")
        exit(1)
    except pd.errors.EmptyDataError:
        print(f"错误：文件 {input_csv_path} 为空")
        exit(1)
    except Exception as e:
        print(f"读取 CSV 文件 {input_csv_path} 时出错: {e}")
        exit(1)

    # 使用RunComfy工作流生成图片
    try:
        # 获取或创建RunComfy实例
        instance_url = runcomfy_service.get_or_create_instance(
            create_new_instance=True,  # 设置为True将创建新实例
            server_type=MACHINE_TYPE,
            estimated_duration=7200
        )
        print(f"获取到RunComfy实例: {instance_url}")
        
        # 处理每个提示词
        for scene in prompts:
            style = scene['style']
            print(f"\n开始生成场景: {scene['name']} (风格: {style})")
            
            # 获取风格配置
            if style not in GEN_CONFIG:
                print(f"不支持的风格: {style}")
                continue
                
            try:
                # 根据风格选择生成函数
                if style == 'flat':
                    generate_func = runcomfy_flat
                elif style == 'watercolor':
                    generate_func = runcomfy_watercolor
                else:
                    print(f"不支持的风格: {style}")
                    continue
                
                # 使用选定的函数执行生成操作
                generated_files = generate_func(
                    prompt=scene['prompt'],
                    instance_url=instance_url,
                    batch_size=GEN_CONFIG[style]['batch_size'],  # 根据风格设置批量大小
                    save_dir=save_dir,
                    output_name=scene['name']  # 使用场景名作为文件名前缀
                )
                print(f"\n场景 {scene['name']} 的图片已保存至:")
                for file in generated_files:
                    print(f"- {file}")
            except Exception as e:
                print(f"生成场景 {scene['name']} 失败: {e}")
                continue  # 继续处理下一个场景
        
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
        script_type='gen',
        image_count=len(prompts),
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
