from fee_growth_calculator import get_fee_growth_inside
from position_updater import update_position, update_position_precise
from GetFeeGrowth import fetch_pool_data


def fetch_aligned_boundary(pool_id: str, mint_block: str, current_block: str, initial_tick: int, label: str) -> tuple:
    """获取在两个区块中对齐后的边界tick数据，确保偏移一致。"""

    target_tick = initial_tick
    last_mint_data = None
    last_current_data = None

    for _ in range(4):
        mint_data = fetch_pool_data(pool_id, mint_block, target_tick)
        if mint_data[0] is None:
            return (None,) * 3

        (
            lower_fee_growth_outside_0_x128,
            lower_fee_growth_outside_1_x128,
            fee_growth_global_0_x128,
            fee_growth_global_1_x128,
            mint_tick_current,
            resolved_tick_mint,
        ) = mint_data

        resolved_tick_mint = resolved_tick_mint if resolved_tick_mint is not None else target_tick

        current_data = fetch_pool_data(pool_id, current_block, resolved_tick_mint)
        if current_data[0] is None:
            return (None,) * 3

        (
            lower_fee_growth_outside_0_x128_current,
            lower_fee_growth_outside_1_x128_current,
            fee_growth_global_0_x128_current,
            fee_growth_global_1_x128_current,
            current_tick,
            resolved_tick_current,
        ) = current_data

        resolved_tick_current = resolved_tick_current if resolved_tick_current is not None else resolved_tick_mint

        last_mint_data = (
            lower_fee_growth_outside_0_x128,
            lower_fee_growth_outside_1_x128,
            fee_growth_global_0_x128,
            fee_growth_global_1_x128,
            mint_tick_current,
            resolved_tick_mint,
        )
        last_current_data = (
            lower_fee_growth_outside_0_x128_current,
            lower_fee_growth_outside_1_x128_current,
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


def main():
    """
    主函数：从链上获取数据，计算区间内手续费增长，然后更新头寸并计算新产生的手续费
    """
    
    # 预定义的参数（不使用手动输入）
    pool_id = "0xC6962004f452bE9203591991D15f6b388e09E8D0"  # USDC/ETH 0.05% pool
    mint_number = "174223195"   # mint时的区块号（更早的区块）
    block_number= "175232417"  # 当前区块号
    tick_lower = -199950 # 下边界tick
    tick_upper = -199530 # 上边界tick
    
    # 代币精度定义 (USDC/ETH pool)
    token0_decimals = 18   # USDC 精度为 6 位小数
    token1_decimals = 6  # ETH 精度为 18 位小数
    token0_symbol = "ETH"
    token1_symbol = "USDC"
    
    print("=== 从链上获取数据 ===")
    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_number} (更早的区块)")
    print(f"当前区块号: {block_number}")
    print(f"查询Tick范围: [{tick_lower}, {tick_upper}]")
    
    print(f"\n第一步：对齐mint区块与当前区块的下边界tick数据")
    lower_mint_data, lower_current_data, tick_lower_effective = fetch_aligned_boundary(
        pool_id,
        mint_number,
        block_number,
        tick_lower,
        "下边界",
    )

    print(f"\n第二步：对齐mint区块与当前区块的上边界tick数据")
    upper_mint_data, upper_current_data, tick_upper_effective = fetch_aligned_boundary(
        pool_id,
        mint_number,
        block_number,
        tick_upper,
        "上边界",
    )

    use_fallback = (
        lower_mint_data is None
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

    # 检查数据获取是否成功
    if use_fallback:
        print("获取链上数据失败，使用示例数据")
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
        tick_lower_effective = tick_lower
        tick_upper_effective = tick_upper
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
    
    # 头寸相关参数
    liquidity = 1e16
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
    
    # 计算总价值（需要价格信息，这里先显示基础信息）
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
    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_number} (更早), 当前区块号: {block_number}")
    if tick_lower_effective != tick_lower or tick_upper_effective != tick_upper:
        print(
            f"价格区间(原始): [{tick_lower}, {tick_upper}], 实际计算使用: [{tick_lower_effective}, {tick_upper_effective}]"
        )
    else:
        print(f"价格区间: [{tick_lower_effective}, {tick_upper_effective}]")
    print(f"Mint时tick: {tick_current_mint}, 当前tick: {tick_current}")
    print(f"流动性: {liquidity}")
    print(f"Mint区块区间内手续费增长: token0={fee_growth_inside_0_x128_mint}, token1={fee_growth_inside_1_x128_mint}")
    print(f"当前区块区间内手续费增长: token0={fee_growth_inside_0_x128_current}, token1={fee_growth_inside_1_x128_current}")
    print(f"从Mint区块到当前区块新产生的手续费:")
    print(f"  {token0_symbol}: {token0_actual:.{token0_decimals+2}f} (原始: {tokens_owed_0_precise:.10f})")
    print(f"  {token1_symbol}: {token1_actual:.{token1_decimals+2}f} (原始: {tokens_owed_1_precise:.10f})")


if __name__ == "__main__":
    main()
