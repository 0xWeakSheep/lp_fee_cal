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
    """
    获取池子数据，如果tick未激活或feeGrowthOutside为0则自动减去60重试
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    # 保存原始tick用于后续调整
    original_tick = tick
    adjustment_made = False

    # 最多尝试10次（防止无限循环）
    for attempt in range(10):
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

        # 检查是否找到tick数据
        if pool_data and 'ticks' in pool_data and pool_data['ticks'] and len(pool_data['ticks']) > 0:
            # 找到了tick数据，检查feeGrowthOutside是否为0
            tick_data = pool_data['ticks'][0]
            pool_info = tick_data['pool']

            # 获取基础数据
            fee_growth_outside_0_x128 = int(tick_data['feeGrowthOutside0X128'])
            fee_growth_outside_1_x128 = int(tick_data['feeGrowthOutside1X128'])
            fee_growth_global_0_x128 = int(pool_info['feeGrowthGlobal0X128'])
            fee_growth_global_1_x128 = int(pool_info['feeGrowthGlobal1X128'])
            current_tick = int(pool_data['tick'])

            # 检查feeGrowthOutside是否为0（表示tick未激活）
            if fee_growth_outside_0_x128 == 0 and fee_growth_outside_1_x128 == 0:
                print(f"⚠️  tick {tick} 的feeGrowthOutside为0，尝试tick {tick - 60}")
                tick -= 60
                adjustment_made = True

                # 可选：设置一个最小tick限制，防止减到负数过大
                if tick < -887220:  # Uniswap V3 的最小tick值
                    print("❌ 已达到最小tick限制，无法继续查找")
                    return None, None, None, None, None
                continue  # 继续循环尝试下一个tick

            # 如果进行了调整，需要对结果进行相应调整
            if adjustment_made:
                tick_diff = original_tick - tick  # 计算调整的tick差值
                print(f"⚠️  原始tick {original_tick} 未激活，使用tick {tick} 的数据")
                print(f"📊 调整幅度: {tick_diff} 个tick")

                # 简单的线性调整（基于tick间距）
                tick_spacing = 60
                adjustment_factor = tick_diff / tick_spacing  # 调整的tick间距数量

                # 调整手续费增长（这里使用简化模型）
                fee_growth_outside_0_x128 = int(fee_growth_outside_0_x128 * (1 + adjustment_factor * 0.01))  # 1%的调整系数
                fee_growth_outside_1_x128 = int(fee_growth_outside_1_x128 * (1 + adjustment_factor * 0.01))

            print(f"✅ 成功获取tick {tick} 的数据")
            return fee_growth_outside_0_x128, fee_growth_outside_1_x128, fee_growth_global_0_x128, fee_growth_global_1_x128, current_tick

        else:
            # 没有找到tick数据，尝试减去60
            print(f"🔄 tick {tick} 未激活，尝试tick {tick - 60}")
            tick -= 60
            adjustment_made = True

            # 可选：设置一个最小tick限制，防止减到负数过大
            if tick < -887220:  # Uniswap V3 的最小tick值
                print("❌ 已达到最小tick限制，无法继续查找")
                return None, None, None, None, None

    # 如果尝试了10次都没找到，返回None
    print(f"❌ 尝试了10次仍未找到激活的tick，原始tick: {original_tick}")
    return None, None, None, None, None

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