def update_position(
    liquidity: int,
    fee_growth_inside_0_x128: int,
    fee_growth_inside_1_x128: int,
    fee_growth_inside_0_last_x128: int = 0,
    fee_growth_inside_1_last_x128: int = 0
) -> tuple[int, int]:
    """
    更新流动性头寸
    
    参数:
    - liquidity: 流动性值
    - fee_growth_inside_0_x128: 当前区间内token0手续费增长
    - fee_growth_inside_1_x128: 当前区间内token1手续费增长
    - fee_growth_inside_0_last_x128: 上次记录的token0手续费增长
    - fee_growth_inside_1_last_x128: 上次记录的token1手续费增长
    
    返回:
    - tuple[int, int]: (新产生的token0手续费, 新产生的token1手续费)
    """
    
    # 检查流动性值
    if liquidity <= 0:
        raise ValueError("NP: 不允许对零流动性头寸进行操作")
    
    # 计算累计手续费
    # Q128 = 2^128
    Q128 = 2 ** 128
    
    tokens_owed_0_new = mul_div(
        fee_growth_inside_0_x128 - fee_growth_inside_0_last_x128,
        liquidity,
        Q128
    )
    
    tokens_owed_1_new = mul_div(
        fee_growth_inside_1_x128 - fee_growth_inside_1_last_x128,
        liquidity,
        Q128
    )
    
    return tokens_owed_0_new, tokens_owed_1_new


def add_delta(x: int, y: int) -> int:
    """
    安全地将流动性变化量添加到当前流动性
    
    参数:
    - x: 当前值
    - y: 变化量
    
    返回:
    - int: 更新后的值
    """
    if y < 0:
        result = x - abs(y)
        if result < 0:
            raise ValueError("流动性不能为负数")
        return result
    else:
        return x + y


def mul_div(a: int, b: int, denominator: int) -> int:
    """
    计算 (a * b) / denominator，避免溢出
    
    参数:
    - a: 被乘数
    - b: 乘数  
    - denominator: 除数
    
    返回:
    - int: 计算结果
    """
    if denominator == 0:
        raise ValueError("除数不能为零")
    
    return (a * b) // denominator


# 示例用法
if __name__ == "__main__":
    # 示例参数
    result = update_position(
        liquidity=1000000,
        fee_growth_inside_0_x128=2000000,
        fee_growth_inside_1_x128=3000000,
        fee_growth_inside_0_last_x128=1500000,
        fee_growth_inside_1_last_x128=2500000
    )
    
    print("新产生的手续费:")
    print(f"token0手续费: {result[0]}")
    print(f"token1手续费: {result[1]}")
