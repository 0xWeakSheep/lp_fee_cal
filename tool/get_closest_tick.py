def get_closest_tick(tick):
    """
    输入一个tick，返回最近的60的倍数
    """
    return round(tick / 60) * 60

# Example usage:
#print(get_closest_tick(123343))  # Output: 123360
#print(get_closest_tick(150344))  # Output: 150360
#print(get_closest_tick(-123342)) # Output: -123360

