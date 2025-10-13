import json
import time
from datetime import datetime
from typing import Union, Optional

import requests


DEFAULT_ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"


def _parse_to_unix_ts(value: Union[str, int, float]) -> int:
    """
    将输入转换为 Unix 时间戳（秒）。
    - 若为数字：直接作为秒（若太大，尝试按毫秒/微秒/纳秒降级）。
    - 若为字符串：先尝试纯数字，再按常见格式解析，最后尝试 python-dateutil。
    """
    if isinstance(value, (int, float)):
        ts = int(value)
        # 处理毫秒/微秒/纳秒级时间戳
        if ts > 10**12:  # 可能是微秒或纳秒
            # 依次尝试纳秒->微秒->毫秒
            for div in (10**9, 10**6, 10**3):
                candidate = ts // div
                if 946684800 <= candidate <= 4102444800:
                    return candidate
        if ts > 10**10 and ts < 10**13:  # 毫秒
            return ts // 1000
        return ts

    s = str(value).strip()
    if s.isdigit():
        ts = int(s)
        if ts > 10**12:
            for div in (10**9, 10**6, 10**3):
                candidate = ts // div
                if 946684800 <= candidate <= 4102444800:
                    return candidate
        if ts > 10**10 and ts < 10**13:
            return ts // 1000
        return ts

    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%m-%d-%Y %H:%M:%S",
        "%m-%d-%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in fmts:
        try:
            return int(datetime.strptime(s, fmt).timestamp())
        except ValueError:
            pass

    try:
        from dateutil import parser
        return int(parser.parse(s).timestamp())
    except Exception:
        raise ValueError(f"无法解析时间输入: {value}")


def _rpc_post_with_retry(
    url: str,
    payload: dict,
    timeout: int = 20,
    max_retries: int = 3,
    backoff_base: float = 0.8,
) -> dict:
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data and data["error"]:
                raise RuntimeError(data["error"])
            return data
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(backoff_base * (2**attempt))
            else:
                break
    assert last_err is not None
    raise last_err


def _get_latest_block_number(rpc_url: str) -> int:
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    data = _rpc_post_with_retry(rpc_url, payload)
    return int(data["result"], 16)


def _get_block_timestamp(rpc_url: str, block_number: int) -> int:
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": [hex(block_number), False],
        "id": 1,
    }
    data = _rpc_post_with_retry(rpc_url, payload)
    result = data.get("result")
    if not result:
        raise RuntimeError("RPC 返回为空")
    return int(result["timestamp"], 16)


def _find_block_before_or_equal(rpc_url: str, target_ts: int, max_steps: int = 64) -> int:
    """
    二分搜索：返回时间戳 <= target_ts 的最近区块号（closest before）。
    """
    latest = _get_latest_block_number(rpc_url)

    # 可选：尝试检查创世区块时间戳（部分链可能不可得）
    try:
        genesis_ts = _get_block_timestamp(rpc_url, 0)
        if target_ts < genesis_ts:
            return 0
    except Exception:
        pass

    lo, hi = 0, latest
    ans = 0
    steps = 0
    while lo <= hi and steps < max_steps:
        mid = (lo + hi) // 2
        ts = _get_block_timestamp(rpc_url, mid)
        if ts == target_ts:
            return mid
        if ts < target_ts:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
        steps += 1
    return ans


def timestamp_to_block(time_or_ts: Union[str, int, float], rpc_url: str = DEFAULT_ARBITRUM_RPC) -> int:
    """
    获取 Arbitrum 链中，不晚于给定时间的最近区块号。
    参数:
      - time_or_ts: 时间字符串或 Unix 时间戳（支持秒/毫秒/微秒/纳秒自动判断）
      - rpc_url: Arbitrum RPC，默认主网
    返回:
      - int: 区块号
    """
    target_ts = _parse_to_unix_ts(time_or_ts)
    return _find_block_before_or_equal(rpc_url, target_ts)

if __name__ == "__main__":
    block = timestamp_to_block("2025-10-10 08:00:00")  # 默认 Arbitrum 主网 RPC
    print(block)

    block2 = timestamp_to_block(1759804800, rpc_url="https://arb1.arbitrum.io/rpc")
    print(block2)