import os
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv
from web3 import Web3

# 加载环境变量
load_dotenv()

RPC_URL = os.getenv("RPC_URL")
API_KEY = os.getenv("RPC_API_KEY")
TICK_SPACING = int(os.getenv("TICK_SPACING", "60"))  # 默认值为60
MAX_SEARCH_ATTEMPTS = int(os.getenv("MAX_SEARCH_ATTEMPTS", "10"))  # 默认搜索10次
REQUEST_TIMEOUT = float(os.getenv("RPC_TIMEOUT", "15"))

# 方法选择器
def _selector(signature: str) -> str:
    return "0x" + Web3.keccak(text=signature).hex()[:8]


SLOT0_SELECTOR = _selector("slot0()")
TICKS_SELECTOR = _selector("ticks(int24)")
FEE_GLOBAL_0_SELECTOR = _selector("feeGrowthGlobal0X128()")
FEE_GLOBAL_1_SELECTOR = _selector("feeGrowthGlobal1X128()")

MIN_TICK = -887220
MAX_TICK = 887220


def _ensure_rpc_url() -> None:
    if not RPC_URL:
        raise RuntimeError("未配置 RPC_URL，请在 .env 中设置")


def _build_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _normalize_block_tag(block_number: str) -> str:
    block_number = (block_number or "").strip()
    if not block_number:
        return "latest"
    lowered = block_number.lower()
    if lowered in {"latest", "safe", "finalized", "pending"}:
        return lowered
    try:
        return hex(int(block_number))
    except ValueError as exc:
        raise ValueError(f"无法解析区块号: {block_number}") from exc


def _rpc_call(payload: dict) -> dict:
    _ensure_rpc_url()
    headers = _build_headers()
    try:
        resp = requests.post(RPC_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise RuntimeError(f"RPC 请求异常: {exc}") from exc

    try:
        res = resp.json()
    except Exception as exc:
        raise RuntimeError(f"RPC 返回内容不是 JSON: {resp.text}") from exc

    if "error" in res:
        raise RuntimeError(f"RPC 调用出错: {res['error']}")
    return res


def _hex_to_int(hex_str: str, signed: bool = False) -> int:
    value = int(hex_str, 16)
    if not signed:
        return value

    bitlen = len(hex_str) * 4
    if value >= 1 << (bitlen - 1):
        value -= 1 << bitlen
    return value


def _slice_word(result_hex: str, index: int) -> str:
    # 去掉0x前缀，每32字节表示一个word
    result_hex = result_hex[2:]
    start = index * 64
    end = start + 64
    return result_hex[start:end]


def _encode_int24(value: int) -> str:
    return value.to_bytes(32, byteorder="big", signed=True).hex()


def _call_function(pool_id: str, selector: str, block_tag: str) -> Optional[str]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": pool_id, "data": selector},
            block_tag,
        ],
    }

    try:
        res = _rpc_call(payload)
    except RuntimeError as err:
        print(err)
        return None

    return res.get("result")


def _call_function_with_input(pool_id: str, selector: str, encoded_args: str, block_tag: str) -> Optional[str]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": pool_id, "data": selector + encoded_args},
            block_tag,
        ],
    }

    try:
        res = _rpc_call(payload)
    except RuntimeError as err:
        print(err)
        return None

    return res.get("result")


def _get_slot0_tick(pool_id: str, block_tag: str) -> Optional[int]:
    result = _call_function(pool_id, SLOT0_SELECTOR, block_tag)
    if not result:
        return None
    tick_hex = _slice_word(result, 1)
    return _hex_to_int(tick_hex, signed=True)


def _get_fee_growth_globals(pool_id: str, block_tag: str) -> Tuple[Optional[int], Optional[int]]:
    fee_growth_global_0 = _call_function(pool_id, FEE_GLOBAL_0_SELECTOR, block_tag)
    fee_growth_global_1 = _call_function(pool_id, FEE_GLOBAL_1_SELECTOR, block_tag)

    if not fee_growth_global_0 or not fee_growth_global_1:
        return None, None

    fg0 = _hex_to_int(_slice_word(fee_growth_global_0, 0))
    fg1 = _hex_to_int(_slice_word(fee_growth_global_1, 0))
    return fg0, fg1


def _get_tick_fee_growth(pool_id: str, block_tag: str, tick: int):
    encoded_tick = _encode_int24(tick)
    result = _call_function_with_input(pool_id, TICKS_SELECTOR, encoded_tick, block_tag)
    if not result or len(result) < 2:
        return None

    fee_growth_outside_0_hex = _slice_word(result, 2)
    fee_growth_outside_1_hex = _slice_word(result, 3)
    initialized_hex = _slice_word(result, 7)

    fee_growth_outside_0 = _hex_to_int(fee_growth_outside_0_hex)
    fee_growth_outside_1 = _hex_to_int(fee_growth_outside_1_hex)
    initialized = _hex_to_int(initialized_hex) != 0

    return fee_growth_outside_0, fee_growth_outside_1, initialized


def fetch_pool_data(pool_id, block_number, tick):
    """
    获取池子数据，如果tick未激活或feeGrowthOutside为0则先向下搜索，再向上搜索
    """
    block_tag = _normalize_block_tag(str(block_number))

    try:
        tick = int(tick)
    except (TypeError, ValueError):
        print(f"无法解析 tick: {tick}")
        return None, None, None, None, None, None

    pool_id = pool_id.strip().lower()
    if not pool_id.startswith("0x"):
        print("pool id 必须是以0x开头的地址")
        return None, None, None, None, None, None

    current_tick = _get_slot0_tick(pool_id, block_tag)
    if current_tick is None:
        print("无法获取当前 tick")
        return None, None, None, None, None, None

    fee_growth_global_0_x128, fee_growth_global_1_x128 = _get_fee_growth_globals(pool_id, block_tag)
    if fee_growth_global_0_x128 is None or fee_growth_global_1_x128 is None:
        print("无法获取全局手续费增长数据")
        return None, None, None, None, None, None

    original_tick = tick
    adjustment_made = False

    # 交替搜索策略: -TICK_SPACING, +TICK_SPACING, -2*TICK_SPACING, +2*TICK_SPACING...
    for attempt in range(1, MAX_SEARCH_ATTEMPTS + 1):
        rpc_data = _get_tick_fee_growth(pool_id, block_tag, tick)

        if rpc_data:
            fee_growth_outside_0_x128, fee_growth_outside_1_x128, initialized = rpc_data

            if initialized and not (fee_growth_outside_0_x128 == 0 and fee_growth_outside_1_x128 == 0):
                if adjustment_made:
                    tick_diff = abs(original_tick - tick)
                    direction_str = "向下" if tick < original_tick else "向上"
                    print(f"⚠️  原始tick {original_tick} 未激活，{direction_str}找到tick {tick} 的数据")
                    print(f"📊 调整幅度: {tick_diff} 个tick")

                    adjustment_factor = tick_diff / TICK_SPACING
                    fee_growth_outside_0_x128 = int(
                        fee_growth_outside_0_x128 * (1 + adjustment_factor * 0.01)
                    )
                    fee_growth_outside_1_x128 = int(
                        fee_growth_outside_1_x128 * (1 + adjustment_factor * 0.01)
                    )

                print(f"✅ 成功获取tick {tick} 的数据")
                return (
                    fee_growth_outside_0_x128,
                    fee_growth_outside_1_x128,
                    fee_growth_global_0_x128,
                    fee_growth_global_1_x128,
                    current_tick,
                    tick,
                )

            if not initialized:
                print(f"⚠️  tick {tick} 未初始化，继续搜索...")
            else:
                print(f"⚠️  tick {tick} 的feeGrowthOutside为0，继续搜索...")
            adjustment_made = True

        step = (attempt + 1) // 2  # 1,1,2,2,3,3...
        direction = -1 if attempt % 2 == 1 else 1  # -1,+1,-1,+1...
        next_tick = original_tick + direction * step * TICK_SPACING

        if next_tick < MIN_TICK or next_tick > MAX_TICK:
            print(f"⚠️  tick {next_tick} 超出边界，跳过")
            continue

        tick = next_tick
        direction_str = "向下" if direction == -1 else "向上"
        print(f"🔄 {direction_str}搜索: tick {tick} (步长 {step * TICK_SPACING})")

    print(f"❌ 尝试了{MAX_SEARCH_ATTEMPTS}次仍未找到激活的tick，原始tick: {original_tick}")
    return None, None, None, None, None, None


# 测试代码
if __name__ == '__main__':
    pool_id = input("请输入 pool id: ")
    block_number = input("请输入 block number: ")
    tick = input("请输入 tick: ")

    fee_growth_outside_0_x128, fee_growth_outside_1_x128, fee_growth_global_0_x128, fee_growth_global_1_x128, current_tick, resolved_tick = fetch_pool_data(pool_id, block_number, tick)

    if fee_growth_outside_0_x128 is not None:
        print(f"Fee Growth Outside 0 X128: {fee_growth_outside_0_x128}")
        print(f"Fee Growth Outside 1 X128: {fee_growth_outside_1_x128}")
        print(f"Fee Growth Global 0 X128: {fee_growth_global_0_x128}")
        print(f"Fee Growth Global 1 X128: {fee_growth_global_1_x128}")
        print(f"Current Tick: {current_tick}")
        print(f"Resolved Tick: {resolved_tick}")
    else:
        print("没有查询到 tick 数据")
