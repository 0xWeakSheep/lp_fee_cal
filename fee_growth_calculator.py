def get_fee_growth_inside(
    tick_lower: int,
    tick_upper: int,
    tick_current: int,
    fee_growth_global_0_x128: int,
    fee_growth_global_1_x128: int,
    lower_fee_growth_outside_0_x128: int,
    lower_fee_growth_outside_1_x128: int,
    upper_fee_growth_outside_0_x128: int,
    upper_fee_growth_outside_1_x128: int
) -> tuple[int, int]:
    """
    计算指定价格区间内的手续费增长
    
    参数:
    - tick_lower: 下边界tick
    - tick_upper: 上边界tick
    - tick_current: 当前tick
    - fee_growth_global_0_x128: 全局token0手续费增长
    - fee_growth_global_1_x128: 全局token1手续费增长
    - lower_fee_growth_outside_0_x128: 下边界外token0手续费增长
    - lower_fee_growth_outside_1_x128: 下边界外token1手续费增长
    - upper_fee_growth_outside_0_x128: 上边界外token0手续费增长
    - upper_fee_growth_outside_1_x128: 上边界外token1手续费增长
    
    返回:
    - tuple[int, int]: (区间内token0手续费增长, 区间内token1手续费增长)
    """
    
    # 计算下方手续费增长
    if tick_current >= tick_lower:
        fee_growth_below_0_x128 = lower_fee_growth_outside_0_x128
        fee_growth_below_1_x128 = lower_fee_growth_outside_1_x128
    else:
        print("小于区间")
        fee_growth_below_0_x128 = fee_growth_global_0_x128 - lower_fee_growth_outside_0_x128
        print("增长")
        print(lower_fee_growth_outside_0_x128)
        print(fee_growth_below_0_x128)
        print("预估")
        print(upper_fee_growth_outside_0_x128-lower_fee_growth_outside_0_x128)
        fee_growth_inside_0_x128=upper_fee_growth_outside_0_x128-lower_fee_growth_outside_0_x128
        fee_growth_below_1_x128 = fee_growth_global_1_x128 - lower_fee_growth_outside_1_x128
        fee_growth_inside_1_x128=upper_fee_growth_outside_1_x128-lower_fee_growth_outside_1_x128
        print(fee_growth_inside_0_x128)
        return fee_growth_inside_0_x128, fee_growth_inside_1_x128
    

    # 计算上方手续费增长
    if tick_current < tick_upper:
        fee_growth_above_0_x128 = upper_fee_growth_outside_0_x128
        fee_growth_above_1_x128 = upper_fee_growth_outside_1_x128
    else:
        print("大于区间")
        fee_growth_above_0_x128 = fee_growth_global_0_x128 - upper_fee_growth_outside_0_x128
        fee_growth_above_1_x128 = fee_growth_global_1_x128 - upper_fee_growth_outside_1_x128

    # 计算区间内手续费增长
    fee_growth_inside_0_x128 = fee_growth_global_0_x128 - fee_growth_below_0_x128 - fee_growth_above_0_x128
    fee_growth_inside_1_x128 = fee_growth_global_1_x128 - fee_growth_below_1_x128 - fee_growth_above_1_x128

    return fee_growth_inside_0_x128, fee_growth_inside_1_x128


# 示例用法
if __name__ == "__main__":
    # 示例参数
    result = get_fee_growth_inside(
        tick_lower=-1000,
        tick_upper=1000,
        tick_current=0,
        fee_growth_global_0_x128=1000000,
        fee_growth_global_1_x128=2000000,
        lower_fee_growth_outside_0_x128=50000,
        lower_fee_growth_outside_1_x128=100000,
        upper_fee_growth_outside_0_x128=30000,
        upper_fee_growth_outside_1_x128=60000
    )
    
    print(f"区间内token0手续费增长: {result[0]}")
    print(f"区间内token1手续费增长: {result[1]}")
