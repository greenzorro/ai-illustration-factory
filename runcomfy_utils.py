'''
File: runcomfy_utils.py
Project: utils
Created: 2025-03-28 02:26:37
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 
'''

import os
import uuid
import json
import requests
import time
import random
import urllib.parse

# RunComfy API Token
keys_file_path = os.path.join(os.path.dirname(__file__), "runcomfy_keys.json")
try:
    with open(keys_file_path, 'r') as f:
        keys = json.load(f)
        RUNCOMFY_USER_ID = keys.get('RUNCOMFY_USER_ID')
        RUNCOMFY_API_TOKEN = keys.get('RUNCOMFY_API_TOKEN')
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"从 {keys_file_path} 加载密钥时出错: {e}")
    RUNCOMFY_USER_ID = None
    RUNCOMFY_API_TOKEN = None

# RunComfy 机器价格字典（Hobby 和 Pro 价格）
RUNCOMFY_MACHINE_PRICES = {
    'hobby': {
        'medium': 0.99,     # 16GB VRAM | 16GB RAM
        'large': 1.75,      # 24GB VRAM | 32GB RAM
        'xlarge': 2.50,     # 48GB VRAM | 48GB RAM
        '2xlarge': 4.99,    # 80GB VRAM | 96GB RAM
        '2xlarge_plus': 7.49 # 80GB VRAM | 180GB RAM
    },
    'pro': {
        'medium': 0.79,     # 16GB VRAM | 16GB RAM
        'large': 1.39,      # 24GB VRAM | 32GB RAM
        'xlarge': 1.99,     # 48GB VRAM | 48GB RAM
        '2xlarge': 3.99,    # 80GB VRAM | 96GB RAM
        '2xlarge_plus': 5.99 # 80GB VRAM | 180GB RAM
    }
}

def generate_seed():
    """生成15位随机正整数
    
    返回:
        int: 生成的随机数
    """
    return random.randint(10**14, (10**15)-1)

class RunComfyService:
    """RunComfy实例管理服务"""
    
    def __init__(self):
        self.instance_info = None
        self.instance_url = None
        self.instance_file = os.path.join(os.path.dirname(__file__), ".runcomfy_instance")
    
    def get_url_from_file(self):
        """从文件读取实例URL"""
        try:
            if os.path.exists(self.instance_file):
                with open(self.instance_file, 'r') as f:
                    data = json.load(f)
                    if data.get('url'):
                        return data['url']
        except Exception as e:
            print(f"读取实例文件失败: {e}")
        return None
        
    def save_url_to_file(self, url):
        """保存实例URL到文件"""
        try:
            with open(self.instance_file, 'w') as f:
                json.dump({'url': url}, f)
            print(f"实例URL已保存到文件: {url}")
        except Exception as e:
            print(f"保存实例文件失败: {e}")
    
    def remove_instance_file(self):
        """删除实例信息文件"""
        try:
            if os.path.exists(self.instance_file):
                os.remove(self.instance_file)
                print("实例信息文件已删除")
        except Exception as e:
            print(f"删除实例文件失败: {e}")

    def get_instance_info(self):
        """获取实例信息
        
        返回:
            dict: 包含实例信息的字典，如果没有可用实例则返回None
        """
        if not RUNCOMFY_API_TOKEN:
            raise ValueError("请设置RUNCOMFY_API_TOKEN")
            
        if not RUNCOMFY_USER_ID:
            raise ValueError("请设置RUNCOMFY_USER_ID")
            
        headers = {'Authorization': f'Bearer {RUNCOMFY_API_TOKEN}'}
        
        # 先检查是否有可用的现有实例
        try:
            servers_url = f"https://api.runcomfy.net/prod/api/users/{RUNCOMFY_USER_ID}/servers"
            response = requests.get(servers_url, headers=headers, timeout=15)
            if response.status_code == 200:
                servers = response.json()
                for server in servers:
                    if server.get('current_status') == 'Ready':
                        server_id = server['server_id']
                        url = f"https://{server_id}-comfyui.runcomfy.com"
                        
                        # 更新实例信息
                        self.instance_url = url
                        self.instance_info = {
                            'url': url,
                            'status': server.get('current_status'),
                            'server_id': server_id
                        }
                        
                        return self.instance_info
        except Exception as e:
            print(f"获取实例列表失败: {e}")
            
        return None
        
    def create_instance(self, server_type="medium", estimated_duration=3600):
        """创建新的RunComfy实例
        
        参数:
            server_type (str): 服务器类型
            estimated_duration (int): 预计运行时间(秒)
            
        返回:
            dict: 包含实例信息的字典
        """
        if not RUNCOMFY_API_TOKEN:
            raise ValueError("请设置RUNCOMFY_API_TOKEN")
            
        if not RUNCOMFY_USER_ID:
            raise ValueError("请设置RUNCOMFY_USER_ID")
            
        headers = {'Authorization': f'Bearer {RUNCOMFY_API_TOKEN}'}
        
        # 1. 获取工作流
        print("正在获取工作流列表...")
        workflows_url = f"https://api.runcomfy.net/prod/api/users/{RUNCOMFY_USER_ID}/workflows"
        response = requests.get(workflows_url, headers=headers, timeout=15)
        response.raise_for_status()
        workflows = response.json()
        
        if not workflows:
            raise ValueError("没有可用的工作流")
        version_id = workflows[0].get('version_id')
        print(f"成功获取工作流，version_id={version_id}")
        
        # 2. 启动实例
        print(f"正在请求启动{server_type}类型实例...")
        launch_url = f"https://api.runcomfy.net/prod/api/users/{RUNCOMFY_USER_ID}/servers"
        request_data = {
            "server_type": server_type,
            "estimated_duration": estimated_duration,
            "workflow_version_id": version_id
        }
        
        response = requests.post(
            launch_url, 
            headers=headers, 
            json=request_data,
            timeout=20
        )
        response.raise_for_status()
        
        server_id = response.json().get('server_id')
        if not server_id:
            raise ValueError("API响应中没有server_id")
            
        print(f"实例创建请求成功，server_id={server_id}")
        
        # 3. 等待就绪
        print("等待实例就绪...")
        status_url = f"https://api.runcomfy.net/prod/api/users/{RUNCOMFY_USER_ID}/servers/{server_id}"
        start_time = time.time()
        max_wait_time = 600  # 10分钟
        last_status = None
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(status_url, headers=headers, timeout=10)
                if response.status_code == 404:
                    print("实例状态查询返回404，可能实例未完全创建，等待5秒...")
                    time.sleep(5)
                    continue
                    
                response.raise_for_status()
                status_data = response.json()
                current_status = status_data.get("current_status")
                
                if current_status != last_status:
                    print(f"实例状态: {current_status}")
                    last_status = current_status
                
                if current_status == "Ready" and status_data.get("main_service_url"):
                    url = f"https://{server_id}-comfyui.runcomfy.com"
                    print(f"实例已就绪: {url}")
                    
                    # 更新实例信息
                    self.instance_url = url
                    self.instance_info = {
                        'url': url,
                        'status': current_status,
                        'server_id': server_id
                    }
                    
                    # 保存URL到文件
                    self.save_url_to_file(url)
                    
                    return self.instance_info
                
                # 根据状态调整等待时间
                if current_status == "Initializing":
                    wait_time = 10  # 初始化阶段等待长一点
                else:
                    wait_time = 5
                    
                time.sleep(wait_time)
                
            except requests.exceptions.RequestException as e:
                print(f"状态检查出错: {e}")
                # 网络错误时使用短暂等待，避免过多的失败请求
                time.sleep(3)
        
        raise Exception(f"等待实例就绪超时 ({max_wait_time}秒)")
    
    def stop_instance(self, server_id=None):
        """停止RunComfy实例
        
        参数:
            server_id (str): 要停止的服务器ID，如果为None则尝试停止当前实例
            
        返回:
            bool: 操作是否成功
        """
        if not RUNCOMFY_API_TOKEN or not RUNCOMFY_USER_ID:
            raise ValueError("请设置RUNCOMFY_API_TOKEN和RUNCOMFY_USER_ID")
        
        headers = {'Authorization': f'Bearer {RUNCOMFY_API_TOKEN}'}
        
        # 如果没有提供server_id，尝试使用当前实例的ID
        if not server_id:
            if not self.instance_info or 'server_id' not in self.instance_info:
                # 尝试获取当前活跃实例
                instance_info = self.get_instance_info()
                if not instance_info or 'server_id' not in instance_info:
                    print("没有找到要停止的实例")
                    return False
                server_id = instance_info['server_id']
            else:
                server_id = self.instance_info['server_id']
        
        print(f"正在停止实例 (server_id={server_id})...")
        
        try:
            stop_url = f"https://api.runcomfy.net/prod/api/users/{RUNCOMFY_USER_ID}/servers/{server_id}"
            response = requests.delete(stop_url, headers=headers, timeout=15)
            
            if response.status_code in [200, 202, 204]:
                print("停止请求已发送，实例将会停止")
                # 清除实例信息
                self.instance_url = None
                self.instance_info = None
                # 删除实例信息文件
                self.remove_instance_file()
                return True
            elif response.status_code == 404:
                print("实例不存在或已停止")
                # 清除实例信息
                self.instance_url = None
                self.instance_info = None
                # 删除实例信息文件
                self.remove_instance_file()
                return True
            else:
                print(f"停止实例失败，状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"停止实例失败: {e}")
            return False
            
    def get_or_create_instance(self, manual_url=None, create_new_instance=True, server_type="medium", estimated_duration=1800):
        """获取现有实例或创建新实例
        
        参数:
            manual_url (str): 手动指定的实例URL
            create_new_instance (bool): 是否在需要时创建新实例
            server_type (str): 服务器类型，可选值：
                - "medium": 16GB VRAM | 16GB RAM，适合基础工作流，SDXL 1024x1024/20步约11秒
                - "large": 24GB VRAM | 32GB RAM，适合中等工作流，SDXL 1024x1024/20步约8秒
                - "xlarge": 48GB VRAM | 48GB RAM，适合大型工作流，SDXL 1024x1024/20步约6.5秒
                - "2xlarge": 80GB VRAM | 96GB RAM，适合超大工作流，SDXL 1024x1024/20步约3.5秒
                - "2xlarge_plus": 80GB VRAM | 180GB RAM，适合内存密集型工作流，SDXL 1024x1024/20步约2.2秒
            estimated_duration (int): 预计运行时间(秒)
            
        返回:
            str: 实例URL
            
        异常:
            ValueError: 未找到可用实例且不允许创建新实例时抛出
        """
        instance_url = None
        
        # 1. 如果指定了manual_url，直接使用
        if manual_url:
            instance_url = manual_url
            print(f"使用手动指定的实例: {instance_url}")
            return instance_url
            
        # 2. 尝试检查是否有现有可用实例
        try:
            print("检查现有实例...")
            # 先尝试从文件获取URL
            file_url = self.get_url_from_file()
            if file_url:
                # 确认这个实例是否仍然可用
                instance_info = self.get_instance_info()
                if instance_info and instance_info['url'] == file_url:
                    instance_url = file_url
                    print(f"使用现有实例: {instance_url}")
                    return instance_url
            
            # 如果没有从文件获取到URL，检查是否有可用实例
            if not instance_url:
                instance_info = self.get_instance_info()
                if instance_info:
                    instance_url = instance_info['url']
                    print(f"使用可用实例: {instance_url}")
                    # 保存URL到文件
                    self.save_url_to_file(instance_url)
                    return instance_url
        except Exception as e:
            print(f"检查现有实例时出错: {e}")
        
        # 3. 如果需要且没有找到可用实例，创建新实例
        if not instance_url and create_new_instance:
            try:
                print("未找到可用实例，创建新的RunComfy实例...")
                instance_info = self.create_instance(server_type=server_type, estimated_duration=estimated_duration)
                instance_url = instance_info['url']
                print(f"成功创建新实例: {instance_url}")
                return instance_url
            except Exception as e:
                print(f"创建新实例失败: {e}")
        
        # 4. 如果没有找到实例且不允许创建，抛出错误
        if not instance_url:
            raise ValueError("未找到可用的RunComfy实例，请确保实例正在运行或允许创建新实例")
        
        return instance_url

# 创建全局RunComfy服务实例
runcomfy_service = RunComfyService()

def runcomfy_workflow(workflow_json, inputs, instance_url, verify_ssl=False, max_retries=5):
    """执行RunComfy工作流
    
    参数:
        workflow_json (dict/str): 工作流JSON对象或文件路径
        inputs (dict): 输入配置
        instance_url (str): ComfyUI实例URL
        verify_ssl (bool): SSL验证
        max_retries (int): 最大重试次数
        
    返回:
        dict: 包含生成文件信息的字典
    """
    headers = {'Authorization': f'Bearer {RUNCOMFY_API_TOKEN}'}
    
    # 加载工作流
    if isinstance(workflow_json, str):
        with open(workflow_json, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
    else:
        workflow = workflow_json
    
    for attempt in range(max_retries):
        try:
            print(f"执行工作流 (第 {attempt + 1}/{max_retries} 次尝试)...")
            client_id = str(uuid.uuid4())
            
            # 处理输入
            if inputs:
                print("正在处理工作流输入...")
                for node_id, input_data in inputs.items():
                    if node_id not in workflow:
                        print(f"警告: 节点ID {node_id} 不在工作流中")
                        continue
                        
                    input_type = input_data.get('type')
                    
                    if input_type in ['image', 'text_and_image']:
                        # 上传图片
                        image_path = input_data.get('image_path', input_data.get('path'))
                        print(f"上传图片: {os.path.basename(image_path)}")
                        upload_url = f"{instance_url}/upload/image"
                        files = [('image', (os.path.basename(image_path), 
                                open(image_path, 'rb'), 
                                'application/octet-stream'))]
                        
                        try:
                            upload_response = requests.post(
                                upload_url, 
                                headers=headers, 
                                data={'overwrite': 'true'}, 
                                files=files, 
                                verify=verify_ssl,
                                timeout=60
                            )
                            upload_response.raise_for_status()
                            print(f"图片上传成功")
                        except Exception as e:
                            print(f"图片上传失败: {e}")
                            raise
                            
                        workflow[node_id]['inputs']['image'] = os.path.basename(image_path)
                        
                    if input_type in ['text', 'text_and_image', 'text_and_images']:
                        workflow[node_id]['inputs']['text'] = input_data['text']
            
            # 提交工作流
            print("正在提交工作流...")
            prompt_url = f"{instance_url}/prompt"
            try:
                response = requests.post(
                    prompt_url,
                    headers=headers,
                    json={"prompt": workflow, "client_id": client_id},
                    verify=verify_ssl,
                    timeout=30
                )
                response.raise_for_status()
                prompt_id = response.json()['prompt_id']
                print(f"工作流提交成功，prompt_id={prompt_id}")
            except Exception as e:
                print(f"工作流提交失败: {e}")
                raise
            
            # 等待执行完成
            print("等待工作流执行完成...")
            history_url = f"{instance_url}/history/{prompt_id}"
            start_time = time.time()
            
            while time.time() - start_time < 600:  # 10分钟超时
                try:
                    response = requests.get(history_url, headers=headers, verify=verify_ssl, timeout=15)
                    response.raise_for_status()
                    history_data = response.json()
                    
                    if prompt_id in history_data:
                        outputs = history_data[prompt_id].get('outputs')
                        if outputs:
                            print(f"工作流执行完成，用时 {time.time() - start_time:.1f} 秒")
                            return {'outputs': outputs}
                    
                    print("工作流正在执行中...")
                    time.sleep(3)
                        
                except Exception as e:
                    print(f"检查工作流状态失败: {e}")
                    time.sleep(5)
            
            raise Exception("工作流执行超时 (10分钟)")
            
        except Exception as e:
            print(f"执行失败: {e}")
            if attempt < max_retries - 1:
                wait_time = 5 * (2 ** attempt)  # 5, 10, 20...
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("达到最大重试次数，操作失败")
                raise

def runcomfy_download_outputs(outputs, instance_url, save_dir, output_name, verify_ssl=False):
    """下载RunComfy工作流的输出文件
    
    参数:
        outputs (dict): 工作流输出数据
        instance_url (str): ComfyUI实例URL
        save_dir (str): 保存目录
        output_name (str): 输出文件名前缀
        verify_ssl (bool): SSL验证
        
    返回:
        list: 保存的文件路径列表
    """
    headers = {'Authorization': f'Bearer {RUNCOMFY_API_TOKEN}'}
    os.makedirs(save_dir, exist_ok=True)
    saved_files = []
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for idx, image in enumerate(node_output['images']):
                params = {
                    "filename": image['filename'],
                    "subfolder": image.get('subfolder', ''),
                    "type": image.get('type', 'output')
                }
                url = f"{instance_url}/view?{urllib.parse.urlencode(params)}"
                
                try:
                    print(f"下载文件 {idx+1}/{len(node_output['images'])}: {image['filename']}")
                    response = requests.get(url, headers=headers, verify=verify_ssl, timeout=30)
                    response.raise_for_status()
                    
                    ext = image['filename'].split('.')[-1]
                    file_path = os.path.join(
                        save_dir, 
                        f"{output_name}_{idx + 1}.{ext}" if len(node_output['images']) > 1 
                        else f"{output_name}.{ext}"
                    )
                    
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    saved_files.append(file_path)
                    print(f"文件已保存: {file_path}")
                except Exception as e:
                    print(f"下载文件失败: {e}")
                    raise
                    
    if not saved_files:
        raise Exception("没有生成任何文件")
        
    print(f"成功下载了 {len(saved_files)} 个文件")
    return saved_files

def calculate_billable_minutes(duration_minutes, startup_time=5):
    """计算实际计费时间（扣除机器启动时间）
    
    参数:
    - duration_minutes: 总运行时长（分钟）
    - startup_time: 机器启动时间（分钟），默认为5分钟
    
    返回:
    - 实际计费时间（分钟）
    """
    return max(0, duration_minutes - startup_time)
