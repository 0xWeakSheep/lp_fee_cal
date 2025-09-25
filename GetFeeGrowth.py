import requests
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

URL = os.getenv("GRAPH_API_URL")
API_KEY = os.getenv("GRAPH_API_KEY")

def build_query(pool_id, block_number, tick):
    tick_id = f"{pool_id}#{tick}"
    return f"""
{{
  pool(
    id: "{pool_id}"
    block: {{number: {block_number}}}
  ) {{
    tick
    ticks(where: {{id: "{tick_id}"}}) {{
      feeGrowthOutside0X128
      feeGrowthOutside1X128
      pool {{
        feeGrowthGlobal0X128
        feeGrowthGlobal1X128
      }}
    }}
  }}
}}
"""

def fetch_pool_data(pool_id, block_number, tick):
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    query = build_query(pool_id, block_number, tick)
    resp = requests.post(URL, json={'query': query}, headers=headers)
    try:
        res = resp.json()
    except Exception:
        print("API返回内容不是JSON：", resp.text)
        return None, None, None, None, None
    if 'data' not in res or 'pool' not in res['data']:
        print("API返回异常：", res)
        return None, None, None, None, None
    
    pool_data = res['data']['pool']
    if not pool_data or 'ticks' not in pool_data or not pool_data['ticks']:
        print("没有查询到 tick 数据")
        print("API返回内容：", res)
        return None, None, None, None, None
    
    tick_data = pool_data['ticks'][0]
    pool_info = tick_data['pool']
    
    # 直接返回多个变量
    fee_growth_outside_0_x128 = int(tick_data['feeGrowthOutside0X128'])
    fee_growth_outside_1_x128 = int(tick_data['feeGrowthOutside1X128'])
    fee_growth_global_0_x128 = int(pool_info['feeGrowthGlobal0X128'])
    fee_growth_global_1_x128 = int(pool_info['feeGrowthGlobal1X128'])
    current_tick = int(pool_data['tick'])
    
    return fee_growth_outside_0_x128, fee_growth_outside_1_x128, fee_growth_global_0_x128, fee_growth_global_1_x128, current_tick

#测试代码
if __name__ == '__main__':
    pool_id = input("请输入 pool id: ")
    block_number = input("请输入 block number: ")
    tick = input("请输入 tick: ")
    
    # 使用多个变量接收返回值
    fee_growth_outside_0_x128, fee_growth_outside_1_x128, fee_growth_global_0_x128, fee_growth_global_1_x128, current_tick = fetch_pool_data(pool_id, block_number, tick)
    
    if fee_growth_outside_0_x128 is not None:
        print(f"Fee Growth Outside 0 X128: {fee_growth_outside_0_x128}")
        print(f"Fee Growth Outside 1 X128: {fee_growth_outside_1_x128}")
        print(f"Fee Growth Global 0 X128: {fee_growth_global_0_x128}")
        print(f"Fee Growth Global 1 X128: {fee_growth_global_1_x128}")
        print(f"Current Tick: {current_tick}")
    else:
        print("没有查询到 tick 数据")