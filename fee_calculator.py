from fee_growth_calculator import get_fee_growth_inside
from position_updater import update_position, update_position_precise
from GetFeeGrowth import fetch_pool_data
import math


def convert_to_token_amount(raw_amount: float, decimals: int) -> float:
    """
    将原始数量转换为实际的代币数量
    
    参数:
    - raw_amount: 原始数量（最小单位）
    - decimals: 代币精度
    
    返回:
    - float: 实际代币数量
    """
    return raw_amount / (10 ** decimals)


def fetch_aligned_boundary(pool_id: str, mint_block: str, current_block: str, initial_tick: int, label: str):
    """获取在两个区块中对齐后的边界tick数据，确保偏移一致。"""

    target_tick = initial_tick
    last_mint_data = None
    last_current_data = None

    for _ in range(4):
        mint_data = fetch_pool_data(pool_id, mint_block, target_tick)
        if mint_data[0] is None:
            return (None,) * 3

        (
            fee_growth_outside_0_x128_mint,
            fee_growth_outside_1_x128_mint,
            fee_growth_global_0_x128_mint,
            fee_growth_global_1_x128_mint,
            mint_tick_current,
            resolved_tick_mint,
        ) = mint_data

        resolved_tick_mint = resolved_tick_mint if resolved_tick_mint is not None else target_tick

        current_data = fetch_pool_data(pool_id, current_block, resolved_tick_mint)
        if current_data[0] is None:
            return (None,) * 3

        (
            fee_growth_outside_0_x128_current,
            fee_growth_outside_1_x128_current,
            fee_growth_global_0_x128_current,
            fee_growth_global_1_x128_current,
            current_tick,
            resolved_tick_current,
        ) = current_data

        resolved_tick_current = resolved_tick_current if resolved_tick_current is not None else resolved_tick_mint

        last_mint_data = (
            fee_growth_outside_0_x128_mint,
            fee_growth_outside_1_x128_mint,
            fee_growth_global_0_x128_mint,
            fee_growth_global_1_x128_mint,
            mint_tick_current,
            resolved_tick_mint,
        )
        last_current_data = (
            fee_growth_outside_0_x128_current,
            fee_growth_outside_1_x128_current,
            fee_growth_global_0_x128_current,
            fee_growth_global_1_x128_current,
            current_tick,
            resolved_tick_current,
        )

        if resolved_tick_current == resolved_tick_mint:
            if resolved_tick_current != initial_tick:
                print(
                    f"⚠️  {label} tick对齐到 {resolved_tick_current} (原始 {initial_tick})"
                )
            return last_mint_data, last_current_data, resolved_tick_current

        print(
            f"⚠️  {label} tick在两个区块解析不同 (mint: {resolved_tick_mint}, 当前: {resolved_tick_current})，尝试重新对齐..."
        )
        target_tick = resolved_tick_current

    print(f"⚠️  {label} tick多次尝试仍未完全一致，使用 {target_tick}")
    return last_mint_data, last_current_data, target_tick


def tick_to_price(tick: int, decimal0: int = 18, decimal1: int = 18) -> float:
    """
    将tick转换为价格（token0/token1）
    
    参数:
    - tick: tick值
    - decimal0, decimal1: 两个币的精度，默认为18
    
    返回:
    - float: 价格
    """
    # Uniswap V3 tick公式的逆运算：price = 1.0001 ^ tick
    price_adj = 1.0001 ** tick
    # 考虑精度调整
    price = price_adj * (10 ** decimal0) / (10 ** decimal1)
    return price
    
def get_sqrt_price_at_tick(tick: int) -> int:
    """
    根据tick计算sqrt价格（Q64.96格式）
    """
    import math
    # 使用更精确的计算方法
    sqrt_price = math.sqrt(1.0001 ** tick) * (2 ** 96)
    return int(sqrt_price)

def calculate_liquidity_from_amounts(
    amount0: float,
    amount1: float,
    tick_lower: int,
    tick_upper: int,
    tick_current: int,
    decimal0: int = 18,
    decimal1: int = 18
) -> int:
    """
    使用Uniswap V3的正确公式计算流动性L
    公式: (Xr + L/sqrt(Pb)) * (Yr + L*sqrt(Pa)) = L^2
    注意：这里的L是原始流动性，包含精度
    """
    # 将代币数量转换为最小单位
    amount0_raw = int(amount0 * (10 ** decimal0))
    amount1_raw = int(amount1 * (10 ** decimal1))
    
    # 计算价格（不包含精度调整）
    price_lower = 1.0001 ** tick_lower
    price_upper = 1.0001 ** tick_upper
    
    # 计算sqrt价格
    sqrt_price_lower = math.sqrt(price_lower)
    sqrt_price_upper = math.sqrt(price_upper)
    
    print(f"调试信息:")
    print(f"  amount0_raw: {amount0_raw}")
    print(f"  amount1_raw: {amount1_raw}")
    print(f"  price_lower: {price_lower}")
    print(f"  price_upper: {price_upper}")
    print(f"  sqrt_price_lower: {sqrt_price_lower}")
    print(f"  sqrt_price_upper: {sqrt_price_upper}")
    
    # 使用Uniswap V3的正确公式
    # (Xr + L/sqrt(Pb)) * (Yr + L*sqrt(Pa)) = L^2
    # 展开: Xr*Yr + Xr*L*sqrt(Pa) + Yr*L/sqrt(Pb) + L^2*sqrt(Pa)/sqrt(Pb) = L^2
    # 整理: L^2*(1 - sqrt(Pa)/sqrt(Pb)) - L*(Xr*sqrt(Pa) + Yr/sqrt(Pb)) - Xr*Yr = 0
    
    # 二次方程系数
    a = 1 - sqrt_price_lower / sqrt_price_upper
    b = -(amount0_raw * sqrt_price_lower + amount1_raw / sqrt_price_upper)
    c = -amount0_raw * amount1_raw
    
    print(f"二次方程系数:")
    print(f"  a: {a}")
    print(f"  b: {b}")
    print(f"  c: {c}")
    
    # 求解二次方程: a*L^2 + b*L + c = 0
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        print("错误: 判别式小于0，无解")
        return 0
    
    # 取正根
    liquidity = (-b + math.sqrt(discriminant)) / (2 * a)
    
    print(f"计算的流动性: {liquidity}")
    
    return int(liquidity)

def calculate_amounts_from_liquidity(
    liquidity: int,
    tick_lower: int,
    tick_upper: int,
    tick_current: int,
    decimal0: int = 18,
    decimal1: int = 18
) -> tuple[float, float]:
    """
    根据流动性L计算对应的amount0和amount1
    
    参数:
    - liquidity: 流动性L
    - tick_lower: 下边界tick
    - tick_upper: 上边界tick
    - tick_current: 当前tick
    - decimal0: token0精度
    - decimal1: token1精度
    
    返回:
    - tuple[float, float]: (amount0, amount1) 实际代币数量
    """
    
    # 计算价格
    price_current = tick_to_price(tick_current, decimal0, decimal1)
    price_lower = tick_to_price(tick_lower, decimal0, decimal1)
    price_upper = tick_to_price(tick_upper, decimal0, decimal1)
    
    # 计算sqrt价格
    sqrt_price_current = math.sqrt(price_current)
    sqrt_price_lower = math.sqrt(price_lower)
    sqrt_price_upper = math.sqrt(price_upper)
    
    # 根据当前价格位置计算代币数量
    if tick_current < tick_lower:
        # 当前价格低于区间，只有token0
        amount0_raw = liquidity * (1/sqrt_price_lower - 1/sqrt_price_upper)
        amount1_raw = 0
    elif tick_current >= tick_upper:
        # 当前价格高于区间，只有token1
        amount0_raw = 0
        amount1_raw = liquidity * (sqrt_price_upper - sqrt_price_lower)
    else:
        # 当前价格在区间内，两种代币都有
        amount0_raw = liquidity * (1/sqrt_price_current - 1/sqrt_price_upper)
        amount1_raw = liquidity * (sqrt_price_current - sqrt_price_lower)
    
    # 转换为实际代币数量
    amount0 = amount0_raw / (10 ** decimal0)
    amount1 = amount1_raw / (10 ** decimal1)
    
    return amount0, amount1


def format_fee_display(raw_int: int, raw_precise: float, decimals: int, symbol: str) -> str:
    """
    格式化手续费显示
    
    参数:
    - raw_int: 原始整数手续费
    - raw_precise: 原始精确手续费
    - decimals: 代币精度
    - symbol: 代币符号
    
    返回:
    - str: 格式化的显示字符串
    """
    actual_int = convert_to_token_amount(raw_int, decimals)
    actual_precise = convert_to_token_amount(raw_precise, decimals)
    
    return f"""
    原始数量 - 整数: {raw_int:,}, 精确: {raw_precise:.10f}
    实际{symbol}数量 - 整数: {actual_int:.{decimals}f}, 精确: {actual_precise:.{decimals+4}f}"""


def calculate_lp_fees(
    pool_id: str,
    mint_block_number: str,
    current_block_number: str,
    tick_lower: int,
    tick_upper: int,
    liquidity: int,
    token0_decimals: int,
    token1_decimals: int,
    token0_symbol: str,
    token1_symbol: str,
    use_fallback_data: bool = False
) -> dict:
    """
    计算LP头寸的手续费收益
    
    参数:
    - pool_id: 池子地址
    - mint_block_number: mint时的区块号
    - current_block_number: 当前区块号
    - tick_lower: 下边界tick
    - tick_upper: 上边界tick
    - liquidity: 流动性数量
    - token0_decimals: token0精度
    - token1_decimals: token1精度
    - token0_symbol: token0符号
    - token1_symbol: token1符号
    - use_fallback_data: 是否使用回退数据（当链上数据获取失败时）
    
    返回:
    - dict: 包含计算结果的字典
    """
    
    print("=== 从链上获取数据 ===")
    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_block_number} (更早的区块)")
    print(f"当前区块号: {current_block_number}")
    print(f"查询Tick范围: [{tick_lower}, {tick_upper}]")

    lower_mint_data = lower_current_data = None
    upper_mint_data = upper_current_data = None
    tick_lower_effective = tick_lower
    tick_upper_effective = tick_upper

    if use_fallback_data:
        print("已启用回退模式，跳过链上tick查询")
    else:
        print(f"\n第一步：对齐mint区块与当前区块的下边界tick数据")
        lower_mint_data, lower_current_data, tick_lower_effective = fetch_aligned_boundary(
            pool_id,
            mint_block_number,
            current_block_number,
            tick_lower,
            "下边界",
        )

        print(f"\n第二步：对齐mint区块与当前区块的上边界tick数据")
        upper_mint_data, upper_current_data, tick_upper_effective = fetch_aligned_boundary(
            pool_id,
            mint_block_number,
            current_block_number,
            tick_upper,
            "上边界",
        )

    use_fallback = (
        use_fallback_data
        or lower_mint_data is None
        or lower_current_data is None
        or upper_mint_data is None
        or upper_current_data is None
    )

    if not use_fallback:
        (
            lower_fee_growth_outside_0_x128_mint,
            lower_fee_growth_outside_1_x128_mint,
            fee_growth_global_0_x128_mint,
            fee_growth_global_1_x128_mint,
            tick_current_mint,
            _,
        ) = lower_mint_data

        (
            lower_fee_growth_outside_0_x128,
            lower_fee_growth_outside_1_x128,
            fee_growth_global_0_x128,
            fee_growth_global_1_x128,
            tick_current,
            _,
        ) = lower_current_data

        (
            upper_fee_growth_outside_0_x128_mint,
            upper_fee_growth_outside_1_x128_mint,
            _,
            _,
            _,
            _,
        ) = upper_mint_data

        (
            upper_fee_growth_outside_0_x128,
            upper_fee_growth_outside_1_x128,
            _,
            _,
            _,
            _,
        ) = upper_current_data

    # 检查数据获取是否成功或使用回退数据
    if use_fallback:
        print("使用示例数据")
        # 使用示例数据 - mint区块
        tick_current_mint = 0
        fee_growth_global_0_x128_mint = 950000
        fee_growth_global_1_x128_mint = 1900000
        lower_fee_growth_outside_0_x128_mint = 45000
        lower_fee_growth_outside_1_x128_mint = 90000
        upper_fee_growth_outside_0_x128_mint = 25000
        upper_fee_growth_outside_1_x128_mint = 50000
        
        # 使用示例数据 - 当前区块
        tick_current = 0
        fee_growth_global_0_x128 = 1000000
        fee_growth_global_1_x128 = 2000000
        lower_fee_growth_outside_0_x128 = 50000
        lower_fee_growth_outside_1_x128 = 100000
        upper_fee_growth_outside_0_x128 = 30000
        upper_fee_growth_outside_1_x128 = 60000
    else:
        print(f"Mint区块下边界Fee Growth Outside 0: {lower_fee_growth_outside_0_x128_mint}")
        print(f"Mint区块下边界Fee Growth Outside 1: {lower_fee_growth_outside_1_x128_mint}")
        print(f"Mint区块上边界Fee Growth Outside 0: {upper_fee_growth_outside_0_x128_mint}")
        print(f"Mint区块上边界Fee Growth Outside 1: {upper_fee_growth_outside_1_x128_mint}")
        print(f"当前区块下边界Fee Growth Outside 0: {lower_fee_growth_outside_0_x128}")
        print(f"当前区块下边界Fee Growth Outside 1: {lower_fee_growth_outside_1_x128}")
        print(f"当前区块上边界Fee Growth Outside 0: {upper_fee_growth_outside_0_x128}")
        print(f"当前区块上边界Fee Growth Outside 1: {upper_fee_growth_outside_1_x128}")
        print(f"当前区块全局Fee Growth 0: {fee_growth_global_0_x128}")
        print(f"当前区块全局Fee Growth 1: {fee_growth_global_1_x128}")
        print(f"当前Tick: {tick_current}")
        if tick_lower_effective != tick_lower or tick_upper_effective != tick_upper:
            print(
                f"使用对齐后的tick范围: 下边界 {tick_lower_effective}, 上边界 {tick_upper_effective}"
            )
    
    # 第五步：计算mint区块的区间内手续费增长
    print("\n第五步：计算mint区块的区间内手续费增长")
    
    # 调用手续费增长计算函数（mint区块）
    fee_growth_inside_0_x128_mint, fee_growth_inside_1_x128_mint = get_fee_growth_inside(
        tick_lower=tick_lower_effective,
        tick_upper=tick_upper_effective,
        tick_current=tick_current_mint,
        fee_growth_global_0_x128=fee_growth_global_0_x128_mint,
        fee_growth_global_1_x128=fee_growth_global_1_x128_mint,
        lower_fee_growth_outside_0_x128=lower_fee_growth_outside_0_x128_mint,
        lower_fee_growth_outside_1_x128=lower_fee_growth_outside_1_x128_mint,
        upper_fee_growth_outside_0_x128=upper_fee_growth_outside_0_x128_mint,
        upper_fee_growth_outside_1_x128=upper_fee_growth_outside_1_x128_mint
    )
    
    print(f"Mint区块区间内token0手续费增长: {fee_growth_inside_0_x128_mint}")
    print(f"Mint区块区间内token1手续费增长: {fee_growth_inside_1_x128_mint}")
    
    # 第六步：计算当前区块的区间内手续费增长
    print("\n第六步：计算当前区块的区间内手续费增长")
    
    # 调用手续费增长计算函数（当前区块）
    fee_growth_inside_0_x128_current, fee_growth_inside_1_x128_current = get_fee_growth_inside(
        tick_lower=tick_lower_effective,
        tick_upper=tick_upper_effective,
        tick_current=tick_current,
        fee_growth_global_0_x128=fee_growth_global_0_x128,
        fee_growth_global_1_x128=fee_growth_global_1_x128,
        lower_fee_growth_outside_0_x128=lower_fee_growth_outside_0_x128,
        lower_fee_growth_outside_1_x128=lower_fee_growth_outside_1_x128,
        upper_fee_growth_outside_0_x128=upper_fee_growth_outside_0_x128,
        upper_fee_growth_outside_1_x128=upper_fee_growth_outside_1_x128
    )
    
    print(f"当前区块区间内token0手续费增长: {fee_growth_inside_0_x128_current}")
    print(f"当前区块区间内token1手续费增长: {fee_growth_inside_1_x128_current}")
    
    # 第七步：更新头寸并计算新产生的手续费
    print("\n第七步：更新头寸并计算新产生的手续费")
    
    # 使用mint区块的手续费增长作为起始值（上次记录的值）
    fee_growth_inside_0_last_x128 = fee_growth_inside_0_x128_mint
    fee_growth_inside_1_last_x128 = fee_growth_inside_1_x128_mint
    
    # 调用update_position_precise函数，计算从mint区块到当前区块之间的手续费变化（包含精确小数）
    tokens_owed_0_int, tokens_owed_0_precise, tokens_owed_1_int, tokens_owed_1_precise = update_position_precise(
        liquidity=liquidity,
        fee_growth_inside_0_x128=fee_growth_inside_0_x128_current,  # 使用当前区块的值
        fee_growth_inside_1_x128=fee_growth_inside_1_x128_current,  # 使用当前区块的值
        fee_growth_inside_0_last_x128=fee_growth_inside_0_last_x128,  # 使用mint区块的值
        fee_growth_inside_1_last_x128=fee_growth_inside_1_last_x128   # 使用mint区块的值
    )
    
    print(f"\n=== 手续费详细信息 ===")
    print(f"Token0 ({token0_symbol})手续费:{format_fee_display(tokens_owed_0_int, tokens_owed_0_precise, token0_decimals, token0_symbol)}")
    print(f"\nToken1 ({token1_symbol})手续费:{format_fee_display(tokens_owed_1_int, tokens_owed_1_precise, token1_decimals, token1_symbol)}")
    
    # 计算总价值
    token0_actual = convert_to_token_amount(tokens_owed_0_precise, token0_decimals)
    token1_actual = convert_to_token_amount(tokens_owed_1_precise, token1_decimals)
    
    print(f"\n=== 手续费汇总 ===")
    print(f"获得的{token0_symbol}: {token0_actual:.{token0_decimals+2}f}")
    print(f"获得的{token1_symbol}: {token1_actual:.{token1_decimals+2}f}")
    
    # 也调用原始版本进行对比
    print("\n=== 原始整数版本对比 ===")
    tokens_owed_0_old, tokens_owed_1_old = update_position(
        liquidity=liquidity,
        fee_growth_inside_0_x128=fee_growth_inside_0_x128_current,
        fee_growth_inside_1_x128=fee_growth_inside_1_x128_current,
        fee_growth_inside_0_last_x128=fee_growth_inside_0_last_x128,
        fee_growth_inside_1_last_x128=fee_growth_inside_1_last_x128
    )
    print(f"原始版本 - token0手续费: {tokens_owed_0_old}")
    print(f"原始版本 - token1手续费: {tokens_owed_1_old}")
    
    # 总结
    print("\n=== 完整流程总结 ===")
    # 计算价格区间
    price_lower_effective = tick_to_price(tick_lower_effective, token0_decimals, token1_decimals)
    price_upper_effective = tick_to_price(tick_upper_effective, token0_decimals, token1_decimals)
    if tick_lower_effective != tick_lower or tick_upper_effective != tick_upper:
        price_lower_original = tick_to_price(tick_lower, token0_decimals, token1_decimals)
        price_upper_original = tick_to_price(tick_upper, token0_decimals, token1_decimals)
    else:
        price_lower_original = price_lower_effective
        price_upper_original = price_upper_effective
    price_mint = tick_to_price(tick_current_mint, token0_decimals, token1_decimals)
    price_current = tick_to_price(tick_current, token0_decimals, token1_decimals)

    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_block_number} (更早), 当前区块号: {current_block_number}")
    if tick_lower_effective != tick_lower or tick_upper_effective != tick_upper:
        print(
            f"价格区间(原始): [{price_lower_original:.6f}, {price_upper_original:.6f}], "
            f"实际计算使用: [{price_lower_effective:.6f}, {price_upper_effective:.6f}] ({token0_symbol}/{token1_symbol})"
        )
    else:
        print(f"价格区间: [{price_lower_effective:.6f}, {price_upper_effective:.6f}] ({token0_symbol}/{token1_symbol})")
    print(f"Mint时价格: {price_mint:.6f} ({token0_symbol}/{token1_symbol}), 当前价格: {price_current:.6f} ({token0_symbol}/{token1_symbol})")
    print(f"流动性: {liquidity}")
    print(f"Mint区块区间内手续费增长: token0={fee_growth_inside_0_x128_mint}, token1={fee_growth_inside_1_x128_mint}")
    print(f"当前区块区间内手续费增长: token0={fee_growth_inside_0_x128_current}, token1={fee_growth_inside_1_x128_current}")
    print(f"从Mint区块到当前区块新产生的手续费:")
    print(f"  {token0_symbol}: {token0_actual:.{token0_decimals+2}f} (原始: {tokens_owed_0_precise:.10f})")
    print(f"  {token1_symbol}: {token1_actual:.{token1_decimals+2}f} (原始: {tokens_owed_1_precise:.10f})")
    
    # 返回结果
    return {
        "pool_id": pool_id,
        "mint_block_number": mint_block_number,
        "current_block_number": current_block_number,
        "tick_lower": tick_lower,
        "tick_upper": tick_upper,
        "tick_lower_effective": tick_lower_effective,
        "tick_upper_effective": tick_upper_effective,
        "tick_current_mint": tick_current_mint,
        "tick_current": tick_current,
        "liquidity": liquidity,
        "fee_growth_inside_0_x128_mint": fee_growth_inside_0_x128_mint,
        "fee_growth_inside_1_x128_mint": fee_growth_inside_1_x128_mint,
        "fee_growth_inside_0_x128_current": fee_growth_inside_0_x128_current,
        "fee_growth_inside_1_x128_current": fee_growth_inside_1_x128_current,
        "tokens_owed_0_int": tokens_owed_0_int,
        "tokens_owed_0_precise": tokens_owed_0_precise,
        "tokens_owed_1_int": tokens_owed_1_int,
        "tokens_owed_1_precise": tokens_owed_1_precise,
        "token0_actual": token0_actual,
        "token1_actual": token1_actual,
        "token0_symbol": token0_symbol,
        "token1_symbol": token1_symbol,
        "token0_decimals": token0_decimals,
        "token1_decimals": token1_decimals
    }


def verify_pool_configuration():
    """
    验证池子配置是否正确
    """
    print("=== 池子配置验证 ===")
    
    # 测试价格计算
    test_tick = -193200
    print(f"测试tick: {test_tick}")
    
    # 假设 ETH 是 token0，USDC 是 token1
    price_eth_usdc = tick_to_price(test_tick, 18, 6)
    print(f"ETH/USDC 价格: {price_eth_usdc:.6f}")
    
    # 假设 USDC 是 token0，ETH 是 token1  
    price_usdc_eth = tick_to_price(test_tick, 6, 18)
    print(f"USDC/ETH 价格: {price_usdc_eth:.6f}")
    
    # 验证反向计算
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'tool'))
    
    from tool.get_tick_by_price import get_tick_by_price
    from tool.get_closest_tick import get_closest_tick
    
    tick_from_price1 = get_closest_tick(get_tick_by_price(price_eth_usdc, 18, 6))
    tick_from_price2 = get_closest_tick(get_tick_by_price(1/price_usdc_eth, 6, 18))
    
    print(f"从价格反推tick (ETH/USDC): {tick_from_price1}")
    print(f"从价格反推tick (USDC/ETH): {tick_from_price2}")
    
    # 检查哪个更接近原始tick
    diff1 = abs(tick_from_price1 - test_tick)
    diff2 = abs(tick_from_price2 - test_tick)
    
    print(f"差异1: {diff1}, 差异2: {diff2}")
    
    if diff1 < diff2:
        print("✅ 正确的配置: ETH是token0, USDC是token1")
        return True, 18, 6, "ETH", "USDC"
    else:
        print("✅ 正确的配置: USDC是token0, ETH是token1")
        return False, 6, 18, "USDC", "ETH"

# ===== 示例使用方式 =====
def example_usage():
    """
    示例使用方式 - 参考原main.py文件的参数
    """
    print("=== LP手续费计算器示例使用 ===\n")
    
    # 验证池子配置
    is_eth_token0, token0_decimals, token1_decimals, token0_symbol, token1_symbol = verify_pool_configuration()
    
    # 参数设置
    pool_id = "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"  # USDC/ETH 0.05% pool
    mint_block_number = "23436334"   # mint时的区块号（更早的区块）
    current_block_number = "23457779"  # 当前区块号
    tick_lower = -194100  # 下边界tick
    tick_upper = -192120 # 上边界tick
    
    # 示例：从代币数量计算流动性
    print("=== 流动性计算示例 ===")
    amount0 = 1.14841738  # 1.14841738 ETH
    amount1 = 5257  # 5257 USDC
    tick_current = -193200  # 当前tick
    
    # 根据验证结果调整代币数量
    if is_eth_token0:
        # ETH是token0, USDC是token1
        eth_amount = amount0
        usdc_amount = amount1
    else:
        # USDC是token0, ETH是token1
        eth_amount = amount1
        usdc_amount = amount0
    
    print(f"调整后的代币数量:")
    print(f"  {token0_symbol}: {eth_amount if is_eth_token0 else usdc_amount}")
    print(f"  {token1_symbol}: {usdc_amount if is_eth_token0 else eth_amount}")
    
    liquidity = calculate_liquidity_from_amounts(
        amount0=eth_amount if is_eth_token0 else usdc_amount,
        amount1=usdc_amount if is_eth_token0 else eth_amount,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        tick_current=tick_current,
        decimal0=token0_decimals,
        decimal1=token1_decimals
    )
    
    print(f"输入: {eth_amount if is_eth_token0 else usdc_amount} {token0_symbol} + {usdc_amount if is_eth_token0 else eth_amount} {token1_symbol}")
    print(f"计算得到的流动性: {liquidity}")
    
    # 验证：从流动性反推代币数量
    calculated_amount0, calculated_amount1 = calculate_amounts_from_liquidity(
        liquidity=liquidity,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        tick_current=tick_current,
        decimal0=token0_decimals,
        decimal1=token1_decimals
    )
    
    print(f"验证: 流动性 {liquidity} 对应的代币数量:")
    print(f"  {token0_symbol}: {calculated_amount0:.6f}")
    print(f"  {token1_symbol}: {calculated_amount1:.2f}")
    
    # 调用计算函数
    result = calculate_lp_fees(
        pool_id=pool_id,
        mint_block_number=mint_block_number,
        current_block_number=current_block_number,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        liquidity=liquidity,
        token0_decimals=token0_decimals,
        token1_decimals=token1_decimals,
        token0_symbol=token0_symbol,
        token1_symbol=token1_symbol,
        use_fallback_data=False  # 设为True可使用示例数据
    )
    
    # 访问返回结果
    print(f"\n=== 函数返回结果 ===")
    print(f"获得的{result['token0_symbol']}: {result['token0_actual']:.{result['token0_decimals']+2}f}")
    print(f"获得的{result['token1_symbol']}: {result['token1_actual']:.{result['token1_decimals']+2}f}")
    print(f"原始精确值 - {result['token0_symbol']}: {result['tokens_owed_0_precise']:.10f}")
    print(f"原始精确值 - {result['token1_symbol']}: {result['tokens_owed_1_precise']:.10f}")
    
    return result


if __name__ == "__main__":
    # 运行示例
    example_usage()
