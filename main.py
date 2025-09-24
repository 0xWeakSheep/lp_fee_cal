from fee_growth_calculator import get_fee_growth_inside
from position_updater import update_position


def main():
    """
    主函数：先计算区间内手续费增长，然后更新头寸并计算新产生的手续费
    """
    
    # 第一步：调用手续费增长计算函数
    print("第一步：计算区间内手续费增长")
    
    # 输入参数
    tick_lower = -1000
    tick_upper = 1000
    tick_current = 0
    fee_growth_global_0_x128 = 1000000
    fee_growth_global_1_x128 = 2000000
    lower_fee_growth_outside_0_x128 = 50000
    lower_fee_growth_outside_1_x128 = 100000
    upper_fee_growth_outside_0_x128 = 30000
    upper_fee_growth_outside_1_x128 = 60000
    
    # 调用第一个函数
    fee_growth_inside_0_x128, fee_growth_inside_1_x128 = get_fee_growth_inside(
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
    
    print(f"区间内token0手续费增长: {fee_growth_inside_0_x128}")
    print(f"区间内token1手续费增长: {fee_growth_inside_1_x128}")
    
    # 第二步：使用第一步的结果调用头寸更新函数
    print("\n第二步：更新头寸并计算新产生的手续费")
    
    # 头寸相关参数
    liquidity = 500000
    
    # 调用第二个函数，使用第一个函数的返回值作为输入
    tokens_owed_0_new, tokens_owed_1_new = update_position(
        liquidity=liquidity,
        fee_growth_inside_0_x128=fee_growth_inside_0_x128,  # 来自第一个函数的返回值
        fee_growth_inside_1_x128=fee_growth_inside_1_x128,  # 来自第一个函数的返回值
    )
    
    print(f"新产生的token0手续费: {tokens_owed_0_new}")
    print(f"新产生的token1手续费: {tokens_owed_1_new}")
    
    # 总结
    print("\n=== 完整流程总结 ===")
    print(f"输入价格区间: [{tick_lower}, {tick_upper}], 当前tick: {tick_current}")
    print(f"流动性: {liquidity}")
    print(f"计算得到的区间内手续费增长: token0={fee_growth_inside_0_x128}, token1={fee_growth_inside_1_x128}")
    print(f"最终新产生的手续费: token0={tokens_owed_0_new}, token1={tokens_owed_1_new}")


if __name__ == "__main__":
    main()
