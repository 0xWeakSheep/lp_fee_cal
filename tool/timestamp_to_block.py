import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import re
import time

# 加载环境变量
load_dotenv()

# 以太坊主网平均区块时间（秒）
ETHEREUM_BLOCK_TIME = 12

def parse_time_to_timestamp(time_input: str) -> int:
    """
    将时间字符串转换为Unix时间戳
    
    支持的格式:
    - "2024-01-01" (日期)
    - "2024-01-01 12:30:00" (日期时间)
    - "2024-01-01T12:30:00" (ISO格式)
    - "2024-01-01T12:30:00Z" (UTC ISO格式)
    - "2024-01-01 12:30:00 UTC" (带时区)
    - "2024-01-01 12:30:00 GMT" (带时区)
    - "2024-01-01 12:30:00+08:00" (带时区偏移)
    - "2024/01/01" (斜杠分隔)
    - "01-01-2024" (美式格式)
    - "01/01/2024" (美式斜杠格式)
    - "2024年1月1日" (中文格式)
    - "2024年1月1日 12:30:00" (中文日期时间)
    
    参数:
    - time_input: 时间字符串
    
    返回:
    - int: Unix时间戳（秒）
    """
    if not time_input or not time_input.strip():
        raise ValueError("时间输入不能为空")
    
    time_input = time_input.strip()
    
    # 处理中文格式
    if '年' in time_input:
        time_input = convert_chinese_time(time_input)
    
    # 尝试多种解析格式
    formats = [
        "%Y-%m-%d %H:%M:%S",           # 2024-01-01 12:30:00
        "%Y-%m-%dT%H:%M:%S",           # 2024-01-01T12:30:00
        "%Y-%m-%dT%H:%M:%SZ",          # 2024-01-01T12:30:00Z
        "%Y-%m-%d %H:%M:%S UTC",       # 2024-01-01 12:30:00 UTC
        "%Y-%m-%d %H:%M:%S GMT",       # 2024-01-01 12:30:00 GMT
        "%Y-%m-%d %H:%M:%S%z",         # 2024-01-01 12:30:00+08:00
        "%Y-%m-%d",                    # 2024-01-01
        "%Y/%m/%d %H:%M:%S",           # 2024/01/01 12:30:00
        "%Y/%m/%d",                    # 2024/01/01
        "%m-%d-%Y %H:%M:%S",           # 01-01-2024 12:30:00
        "%m-%d-%Y",                    # 01-01-2024
        "%m/%d/%Y %H:%M:%S",           # 01/01/2024 12:30:00
        "%m/%d/%Y",                    # 01/01/2024
        "%d-%m-%Y %H:%M:%S",           # 01-01-2024 12:30:00 (欧洲格式)
        "%d-%m-%Y",                    # 01-01-2024 (欧洲格式)
        "%d/%m/%Y %H:%M:%S",           # 01/01/2024 12:30:00 (欧洲格式)
        "%d/%m/%Y",                    # 01/01/2024 (欧洲格式)
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_input, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue
    
    # 如果所有格式都失败，尝试使用 dateutil 解析
    try:
        from dateutil import parser
        dt = parser.parse(time_input)
        return int(dt.timestamp())
    except ImportError:
        pass
    except Exception:
        pass
    
    raise ValueError(f"无法解析时间格式: {time_input}")

def convert_chinese_time(time_str: str) -> str:
    """
    将中文时间格式转换为标准格式
    
    参数:
    - time_str: 中文时间字符串
    
    返回:
    - str: 标准格式时间字符串
    """
    # 中文数字到阿拉伯数字的映射
    chinese_digits = {
        '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
        '五': '5', '六': '6', '七': '7', '八': '8', '九': '9',
        '十': '10', '十一': '11', '十二': '12'
    }
    
    # 替换中文数字
    for chinese, arabic in chinese_digits.items():
        time_str = time_str.replace(chinese, arabic)
    
    # 处理中文日期格式
    # 2024年1月1日 -> 2024-01-01
    pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
    match = re.search(pattern, time_str)
    if match:
        year, month, day = match.groups()
        date_part = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # 检查是否有时间部分
        time_part = time_str[match.end():].strip()
        if time_part:
            # 提取时间部分 (如 " 12:30:00")
            time_match = re.search(r'(\d{1,2}):(\d{1,2}):(\d{1,2})', time_part)
            if time_match:
                hour, minute, second = time_match.groups()
                return f"{date_part} {hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
            else:
                return f"{date_part} 00:00:00"
        else:
            return f"{date_part} 00:00:00"
    
    return time_str

def time_to_block_number(time_input: str, api_key: str = None) -> int:
    """
    将时间字符串直接转换为区块号
    
    参数:
    - time_input: 时间字符串（支持多种格式）
    - api_key: Etherscan API密钥（可选）
    
    返回:
    - int: 最接近的区块号
    """
    timestamp = parse_time_to_timestamp(time_input)
    return timestamp_to_block_number_etherscan(timestamp, api_key)

def make_request_with_retry(url: str, params: dict, max_retries: int = 3, timeout: int = 30) -> dict:
    """
    带重试机制的HTTP请求
    
    参数:
    - url: 请求URL
    - params: 请求参数
    - max_retries: 最大重试次数
    - timeout: 超时时间（秒）
    
    返回:
    - dict: API响应数据
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            data = response.json()
            return data
        except requests.exceptions.SSLError as e:
            print(f"SSL错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                raise Exception(f"SSL连接失败，已重试 {max_retries} 次")
        except requests.exceptions.Timeout as e:
            print(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise Exception(f"请求超时，已重试 {max_retries} 次")
        except requests.exceptions.RequestException as e:
            print(f"请求错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise Exception(f"请求失败，已重试 {max_retries} 次")
        except Exception as e:
            raise Exception(f"未知错误: {str(e)}")

def timestamp_to_block_number_etherscan(timestamp: int, api_key: str = None) -> int:
    """
    使用 Etherscan API 将时间戳转换为区块号
    
    参数:
    - timestamp: Unix时间戳（秒）
    - api_key: Etherscan API密钥（可选）
    
    返回:
    - int: 最接近的区块号
    """
    if api_key is None:
        api_key = os.getenv("ETHERSCAN_API_KEY")
    
    if not api_key:
        raise ValueError("需要提供 Etherscan API 密钥")
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": timestamp,
        "closest": "before",
        "apikey": api_key
    }
    
    try:
        data = make_request_with_retry(url, params)
        
        if data["status"] == "1":
            return int(data["result"])
        else:
            raise Exception(f"Etherscan API 错误: {data.get('message', '未知错误')}")
            
    except Exception as e:
        raise Exception(f"获取区块号失败: {str(e)}")

def timestamp_to_block_number_estimation(timestamp: int, reference_block: int = None, reference_timestamp: int = None) -> int:
    """
    通过估算将时间戳转换为区块号
    
    参数:
    - timestamp: 目标时间戳（秒）
    - reference_block: 参考区块号（可选，默认使用当前区块）
    - reference_timestamp: 参考时间戳（可选，默认使用当前时间）
    
    返回:
    - int: 估算的区块号
    """
    if reference_timestamp is None:
        reference_timestamp = int(datetime.now().timestamp())
    
    if reference_block is None:
        # 使用一个合理的当前区块号作为参考
        # 注意：这个值需要定期更新
        reference_block = 19000000  # 示例值，需要根据实际情况调整
    
    # 计算时间差（秒）
    time_diff = timestamp - reference_timestamp
    
    # 计算区块差
    block_diff = time_diff // ETHEREUM_BLOCK_TIME
    
    # 返回估算的区块号
    return reference_block + block_diff

def get_block_timestamp_etherscan(block_number: int, api_key: str = None) -> int:
    """
    使用 Etherscan API 获取指定区块的时间戳
    
    参数:
    - block_number: 区块号
    - api_key: Etherscan API密钥（可选）
    
    返回:
    - int: 区块时间戳
    """
    if api_key is None:
        api_key = os.getenv("ETHERSCAN_API_KEY")
    
    if not api_key:
        raise ValueError("需要提供 Etherscan API 密钥")
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "proxy",
        "action": "eth_getBlockByNumber",
        "tag": hex(block_number),
        "boolean": "true",
        "apikey": api_key
    }
    
    try:
        data = make_request_with_retry(url, params)
        
        if "result" in data and data["result"]:
            # 将十六进制时间戳转换为十进制
            return int(data["result"]["timestamp"], 16)
        else:
            raise Exception(f"Etherscan API 错误: {data.get('message', '未知错误')}")
            
    except Exception as e:
        raise Exception(f"获取区块时间戳失败: {str(e)}")

def format_timestamp(timestamp: int) -> str:
    """
    格式化时间戳为可读的日期时间
    
    参数:
    - timestamp: Unix时间戳（秒）
    
    返回:
    - str: 格式化的日期时间字符串
    """
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S UTC")

# 使用示例
if __name__ == "__main__":
    print("\n=== 时间到区块号转换测试 ===")
    # 使用一个具体的时间进行测试
    target_time = "2025-09-28 08:00:00"
    
    try:
        # 方法1：直接使用时间字符串
        block_number = time_to_block_number(target_time)
        print(f"✅ 时间 '{target_time}' 对应的区块号: {block_number}")
        
        # 验证：获取该区块的时间戳（可选，如果网络不稳定可以跳过）
        try:
            block_timestamp = get_block_timestamp_etherscan(block_number)
            print(f"✅ 区块 {block_number} 的时间戳: {block_timestamp} ({format_timestamp(block_timestamp)})")
        except Exception as e:
            print(f"⚠️  验证区块时间戳失败（网络问题）: {e}")
            print(f"✅ 但区块号转换成功: {block_number}")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        
        # 备用方案：使用估算方法
        try:
            print("\n🔄 尝试使用估算方法...")
            timestamp = parse_time_to_timestamp(target_time)
            estimated_block = timestamp_to_block_number_estimation(timestamp)
            print(f"✅ 使用估算方法获取的区块号: {estimated_block}")
            print(f"⚠️  注意：这是估算值，可能不够精确")
        except Exception as e2:
            print(f"❌ 估算方法也失败: {e2}")
