def update_position_precise(
    liquidity: int,
    fee_growth_inside_0_x128: int,
    fee_growth_inside_1_x128: int,
    fee_growth_inside_0_last_x128: int,
    fee_growth_inside_1_last_x128: int
) -> tuple[int, float, int, float]:
    """
    更新流动性头寸（精确版本，包含小数结果）
    
    参数:
    - liquidity: 流动性值
    - fee_growth_inside_0_x128: 当前区间内token0手续费增长
    - fee_growth_inside_1_x128: 当前区间内token1手续费增长
    - fee_growth_inside_0_last_x128: 上次记录的token0手续费增长
    - fee_growth_inside_1_last_x128: 上次记录的token1手续费增长
    
    返回:
    - tuple[int, float, int, float]: (token0整数手续费, token0精确手续费, token1整数手续费, token1精确手续费)
    """
    
    # 检查流动性值
    if liquidity <= 0:
        raise ValueError("NP: 不允许对零流动性头寸进行操作")
    
    # 计算累计手续费
    # Q128 = 2^128
    Q128 = 2 ** 128
    
    # 计算token0手续费
    fee_growth_diff_0 = fee_growth_inside_0_x128 - fee_growth_inside_0_last_x128
    print(f"Token0手续费增长差值: {fee_growth_diff_0}")
    
    tokens_owed_0_int, tokens_owed_0_precise = mul_div_with_precision(
        fee_growth_diff_0,
        liquidity,
        Q128
    )
    
    # 计算token1手续费
    fee_growth_diff_1 = fee_growth_inside_1_x128 - fee_growth_inside_1_last_x128
    print(f"Token1手续费增长差值: {fee_growth_diff_1}")
    
    tokens_owed_1_int, tokens_owed_1_precise = mul_div_with_precision(
        fee_growth_diff_1,
        liquidity,
        Q128
    )
    
    print(f"流动性: {liquidity}")
    print(f"Q128: {Q128}")
    print(f"Token0手续费 - 整数: {tokens_owed_0_int}, 精确: {tokens_owed_0_precise:.10f}")
    print(f"Token1手续费 - 整数: {tokens_owed_1_int}, 精确: {tokens_owed_1_precise:.10f}")
    
    return tokens_owed_0_int, tokens_owed_0_precise, tokens_owed_1_int, tokens_owed_1_precise


def update_position(
    liquidity: int,
    fee_growth_inside_0_x128: int,
    fee_growth_inside_1_x128: int,
    fee_growth_inside_0_last_x128: int,
    fee_growth_inside_1_last_x128: int
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
    
    # 计算token0手续费
    fee_growth_diff_0 = fee_growth_inside_0_x128 - fee_growth_inside_0_last_x128
    print(f"Token0手续费增长差值: {fee_growth_diff_0}")
    
    tokens_owed_0_new = mul_div(
        fee_growth_diff_0,
        liquidity,
        Q128
    )
    
    # 计算token1手续费
    fee_growth_diff_1 = fee_growth_inside_1_x128 - fee_growth_inside_1_last_x128
    print(f"Token1手续费增长差值: {fee_growth_diff_1}")
    
    tokens_owed_1_new = mul_div(
        fee_growth_diff_1,
        liquidity,
        Q128
    )
    
    print(f"流动性: {liquidity}")
    print(f"Q128: {Q128}")
    print(f"计算结果 - Token0手续费: {tokens_owed_0_new}")
    print(f"计算结果 - Token1手续费: {tokens_owed_1_new}")
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


def mul_div_with_precision(a: int, b: int, denominator: int) -> tuple[int, float]:
    """
    计算 (a * b) / denominator，返回整数结果和精确的浮点数结果
    
    参数:
    - a: 被乘数
    - b: 乘数  
    - denominator: 除数
    
    返回:
    - tuple[int, float]: (整数结果, 精确的浮点数结果)
    """
    if denominator == 0:
        raise ValueError("除数不能为零")
    
    numerator = a * b
    integer_result = numerator // denominator
    precise_result = numerator / denominator
    
    return integer_result, precise_result


def mul_div(a: int, b: int, denominator: int) -> int:
    """
    计算 (a * b) / denominator，避免溢出
    使用Python的高精度整数运算，确保大数计算的准确性
    
    参数:
    - a: 被乘数
    - b: 乘数  
    - denominator: 除数
    
    返回:
    - int: 计算结果
    """
    if denominator == 0:
        raise ValueError("除数不能为零")
    
    # 使用Python的高精度整数运算
    # Python的int类型本身就是bigint，可以处理任意大的整数
    numerator = a * b
    result = numerator // denominator
    
    # 添加调试信息，包括比例分析
    print(f"mul_div计算: ({a} * {b}) // {denominator}")
    print(f"分子: {numerator}")
    print(f"分母: {denominator}")
    print(f"比例: {numerator / denominator:.10f}")
    print(f"整数除法结果: {result}")
    
    # 检查是否存在精度损失
    if numerator > 0 and result == 0:
        print(f"警告: 精度损失! 分子({numerator})大于0但整数除法结果为0")
        print(f"这意味着手续费非常小，小于1个最小单位")
    
    return result


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
