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
    
    # 第一步：从链上获取mint区块的lower tick数据
    print(f"\n第一步：获取mint区块({mint_block_number})的下边界tick数据")
    lower_fee_growth_outside_0_x128_mint, lower_fee_growth_outside_1_x128_mint, fee_growth_global_0_x128_mint, fee_growth_global_1_x128_mint, tick_current_mint = fetch_pool_data(pool_id, mint_block_number, tick_lower)
    
    # 第二步：获取mint区块的上边界tick数据
    print(f"\n第二步：获取mint区块({mint_block_number})的上边界tick数据")
    upper_fee_growth_outside_0_x128_mint, upper_fee_growth_outside_1_x128_mint, _, _, _ = fetch_pool_data(pool_id, mint_block_number, tick_upper)
    
    # 第三步：获取当前区块的数据
    print(f"\n第三步：获取当前区块({current_block_number})的下边界tick数据")
    lower_fee_growth_outside_0_x128, lower_fee_growth_outside_1_x128, fee_growth_global_0_x128, fee_growth_global_1_x128, tick_current = fetch_pool_data(pool_id, current_block_number, tick_lower)
    
    print(f"\n第四步：获取当前区块({current_block_number})的上边界tick数据")
    upper_fee_growth_outside_0_x128, upper_fee_growth_outside_1_x128, _, _, _ = fetch_pool_data(pool_id, current_block_number, tick_upper)
    
    # 检查数据获取是否成功或使用回退数据
    if (use_fallback_data or 
        lower_fee_growth_outside_0_x128_mint is None or upper_fee_growth_outside_0_x128_mint is None or 
        lower_fee_growth_outside_0_x128 is None or upper_fee_growth_outside_0_x128 is None):
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
    price_lower = tick_to_price(tick_lower, token0_decimals, token1_decimals)
    price_upper = tick_to_price(tick_upper, token0_decimals, token1_decimals)
    price_mint = tick_to_price(tick_current_mint, token0_decimals, token1_decimals)
    price_current = tick_to_price(tick_current, token0_decimals, token1_decimals)
    
    print(f"Pool ID: {pool_id}")
    print(f"Mint区块号: {mint_block_number} (更早), 当前区块号: {current_block_number}")
    print(f"价格区间: [{price_lower:.6f}, {price_upper:.6f}] ({token0_symbol}/{token1_symbol})")
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


# ===== 示例使用方式 =====
def example_usage():
    """
    示例使用方式 - 参考原main.py文件的参数
    """
    print("=== LP手续费计算器示例使用 ===\n")
    
    # 参数设置（参考原main.py文件）
    pool_id = "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36"  # USDC/ETH 0.05% pool
    mint_block_number = "18408173"   # mint时的区块号（更早的区块）
    current_block_number = "23438173"  # 当前区块号
    tick_lower = -200580  # 下边界tick
    tick_upper = -191220  # 上边界tick
    liquidity = 500000    # 流动性数量
    
    # 代币精度定义 (USDC/ETH pool)
    token0_decimals = 18   # ETH 精度为 18 位小数
    token1_decimals = 6    # USDC 精度为 6 位小数
    token0_symbol = "ETH"
    token1_symbol = "USDC"
    
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
