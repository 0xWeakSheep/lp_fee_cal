import requests

URL = "https://gateway.thegraph.com/api/subgraphs/id/HyW7A86UEdYVt5b9Lrw8W2F98yKecerHKutZTRbSCX27"
API_KEY = "5762403578020d8bca2128a9f926a746"  # 请替换为你的真实 API key

def build_query(pool_id, block_number):
    return f"""
{{
  pool(
    id: "{pool_id}"
    block: {{number: {block_number}}}
  ) {{
    feeGrowthGlobal1X128
    feeGrowthGlobal0X128
  }}
}}
"""

def fetch_pool_data(pool_id, block_number):
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    query = build_query(pool_id, block_number)
    resp = requests.post(URL, json={'query': query}, headers=headers)
    try:
        res = resp.json()
    except Exception:
        print("API返回内容不是JSON：", resp.text)
        return None
    if res is None or 'data' not in res or res['data'] is None or 'pool' not in res['data']:
        print("API返回异常：", res)
        return None
    return res['data']['pool']




RPC_URL = "https://arb-mainnet.g.alchemy.com/v2/TuzT5JFAHBLhy4X9r8TovBc_woRguvNW"


def get_block_number_by_timestamp(target_timestamp, max_iterations=100):
    try:
        target = int(target_timestamp)
    except (TypeError, ValueError):
        print("时间戳格式错误：", target_timestamp)
        return None
    if target < 0:
        print("时间戳不能为负数：", target)
        return None

    print(f"[get_block_number_by_timestamp] 目标时间戳: {target}")

    payload_latest = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_blockNumber",
        "params": []
    }
    try:
        resp_latest = requests.post(RPC_URL, json=payload_latest, timeout=10)
        resp_latest.raise_for_status()
        result_latest = resp_latest.json()
        highest_block = int(result_latest.get("result"), 16)
    except (requests.RequestException, ValueError, TypeError) as exc:
        print("获取最新区块失败：", exc)
        return None

    print(f"[get_block_number_by_timestamp] 最新区块号: {highest_block}")

    low, high = 0, highest_block
    best_block = None
    iterations = 0

    while low <= high and iterations < max_iterations:
        iterations += 1
        mid = (low + high) // 2
        print(f"[get_block_number_by_timestamp] 第{iterations}次迭代，当前区块范围: {low}-{high}，尝试区块: {mid}")
        payload_block = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getBlockByNumber",
            "params": [hex(mid), False]
        }
        try:
            resp_block = requests.post(RPC_URL, json=payload_block, timeout=10)
            resp_block.raise_for_status()
            block_data = resp_block.json()
            timestamp_hex = block_data.get("result", {}).get("timestamp")
            block_timestamp = int(timestamp_hex, 16)
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            print("获取区块信息失败：", exc)
            return None

        print(f"[get_block_number_by_timestamp] 区块 {mid} 时间戳: {block_timestamp}")

        if block_timestamp == target:
            print(f"[get_block_number_by_timestamp] 精确匹配到区块: {mid}")
            return mid
        if block_timestamp < target:
            best_block = mid
            low = mid + 1
        else:
            high = mid - 1

    print(f"[get_block_number_by_timestamp] 查找结束，返回区块: {best_block}")
    return best_block









def fetch_pool_series_by_blockday(start_timestamp, end_timestamp, blockday=345600, pool_id=None):
    pool_id = pool_id or ""
    start_block = get_block_number_by_timestamp(start_timestamp)
    if start_block is None:
        return []

    if end_timestamp == start_timestamp:
        end_block = start_block
    else:
        end_block = get_block_number_by_timestamp(end_timestamp)
    if start_block is None or end_block is None or not pool_id:
        return []
    if blockday is None:
        blockday = 345600
    try:
        step = max(1, int(blockday))
    except (TypeError, ValueError):
        step = 345600
    data_points = []
    current_block = min(start_block, end_block)
    target_block = max(start_block, end_block)
    while current_block <= target_block:
        pool_data = fetch_pool_data(pool_id, current_block)
        if pool_data:
            enriched = pool_data.copy()
            enriched['blockNumber'] = current_block
            data_points.append(enriched)
        current_block += step
    if current_block - step < target_block and target_block != start_block:
        final_data = fetch_pool_data(pool_id, target_block)
        if final_data:
            enriched_final = final_data.copy()
            enriched_final['blockNumber'] = target_block
            data_points.append(enriched_final)
    return data_points

#测试代码
if __name__ == '__main__':
    pool_id = input("请输入 pool id: ")
    block_number = input("请输入 block number: ")
    pool_data = fetch_pool_data(pool_id, block_number)
    if pool_data:
        print("pool数据：", pool_data)
    else:
        print("没有查询到 pool 数据")
