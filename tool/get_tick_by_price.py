from get_closest_tick import get_closest_tick

def get_tick_by_price(price, decimal0=18, decimal1=18):
    """
    输入价格，返回tick
    price: 价格（token0/token1）
    decimal0, decimal1: 两个币的精度，默认为18
    """
    import math
    # Uniswap V3 tick公式：tick = log(price) / log(1.0001)
    # 需要考虑精度
    price_adj = price * (10 ** decimal1) / (10 ** decimal0)
    tick = math.log(price_adj) / math.log(1.0001)
    return tick

#use example
print(get_tick_by_price(4551, 18, 6))  # Output: -192088.79227850618
print(get_tick_by_price(0.5, 6, 18))  # Output: 269392.20806621236
print(get_tick_by_price(1, 18, 18))  # Output: 0

print(get_closest_tick(get_tick_by_price(4071, 18, 6)))  # Output: -193200
print(get_closest_tick(get_tick_by_price(0.0005, 6, 18)))  # Output: 200340
print(get_closest_tick(get_tick_by_price(1, 18, 18)))  # Output: 0