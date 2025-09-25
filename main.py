from fee_growth_calculator import get_fee_growth_inside
from position_updater import update_position
from GetFeeGrowth import fetch_pool_data


def main():
    """
    主函数：从链上获取数据，计算区间内手续费增长，然后更新头寸并计算新产生的手续费
    """
    
    # 预定义的参数（不使用手动输入）
    pool_id = "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"  # USDC/ETH 0.05% pool
    mint_number = "23408173"   # mint时的区块号（更早的区块）
    block_number = "23438173"  # 当前区块号
    tick_lower = -201300 # 下边界tick
    tick_upper = -191340  # 上边界tick
    
    print("=== 从链上获取数据 ===")
    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_number} (更早的区块)")
    print(f"当前区块号: {block_number}")
    print(f"查询Tick范围: [{tick_lower}, {tick_upper}]")
    
    # 第一步：从链上获取mint区块的lower tick数据
    print(f"\n第一步：获取mint区块({mint_number})的下边界tick数据")
    lower_fee_growth_outside_0_x128_mint, lower_fee_growth_outside_1_x128_mint, fee_growth_global_0_x128_mint, fee_growth_global_1_x128_mint, tick_current_mint = fetch_pool_data(pool_id, mint_number, tick_lower)
    
    # 第二步：获取mint区块的上边界tick数据
    print(f"\n第二步：获取mint区块({mint_number})的上边界tick数据")
    upper_fee_growth_outside_0_x128_mint, upper_fee_growth_outside_1_x128_mint, _, _, _ = fetch_pool_data(pool_id, mint_number, tick_upper)
    
    # 第三步：获取当前区块的数据
    print(f"\n第三步：获取当前区块({block_number})的下边界tick数据")
    lower_fee_growth_outside_0_x128, lower_fee_growth_outside_1_x128, fee_growth_global_0_x128, fee_growth_global_1_x128, tick_current = fetch_pool_data(pool_id, block_number, tick_lower)
    
    print(f"\n第四步：获取当前区块({block_number})的上边界tick数据")
    upper_fee_growth_outside_0_x128, upper_fee_growth_outside_1_x128, _, _, _ = fetch_pool_data(pool_id, block_number, tick_upper)
    
    # 检查数据获取是否成功
    if (lower_fee_growth_outside_0_x128_mint is None or upper_fee_growth_outside_0_x128_mint is None or 
        lower_fee_growth_outside_0_x128 is None or upper_fee_growth_outside_0_x128 is None):
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
    
    # 第五步：计算mint区块的区间内手续费增长
    print("\n第五步：计算mint区块的区间内手续费增长")
    
    # 调用手续费增长计算函数（mint区块）
    fee_growth_inside_0_x128_mint, fee_growth_inside_1_x128_mint = get_fee_growth_inside(
        tick_lower=tick_lower,
        tick_upper=tick_upper,
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
        tick_lower=tick_lower,
        tick_upper=tick_upper,
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
    liquidity = 500000
    # 使用mint区块的手续费增长作为起始值（上次记录的值）
    fee_growth_inside_0_last_x128 = fee_growth_inside_0_x128_mint
    fee_growth_inside_1_last_x128 = fee_growth_inside_1_x128_mint
    
    # 调用update_position函数，计算从mint区块到当前区块之间的手续费变化
    tokens_owed_0_new, tokens_owed_1_new = update_position(
        liquidity=liquidity,
        fee_growth_inside_0_x128=fee_growth_inside_0_x128_current,  # 使用当前区块的值
        fee_growth_inside_1_x128=fee_growth_inside_1_x128_current,  # 使用当前区块的值
        fee_growth_inside_0_last_x128=fee_growth_inside_0_last_x128,  # 使用mint区块的值
        fee_growth_inside_1_last_x128=fee_growth_inside_1_last_x128   # 使用mint区块的值
    )
    
    print(f"新产生的token0手续费: {tokens_owed_0_new}")
    print(f"新产生的token1手续费: {tokens_owed_1_new}")
    
    # 总结
    print("\n=== 完整流程总结 ===")
    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_number} (更早), 当前区块号: {block_number}")
    print(f"价格区间: [{tick_lower}, {tick_upper}]")
    print(f"Mint时tick: {tick_current_mint}, 当前tick: {tick_current}")
    print(f"流动性: {liquidity}")
    print(f"Mint区块区间内手续费增长: token0={fee_growth_inside_0_x128_mint}, token1={fee_growth_inside_1_x128_mint}")
    print(f"当前区块区间内手续费增长: token0={fee_growth_inside_0_x128_current}, token1={fee_growth_inside_1_x128_current}")
    print(f"从Mint区块到当前区块新产生的手续费: token0={tokens_owed_0_new}, token1={tokens_owed_1_new}")


if __name__ == "__main__":
    main()
