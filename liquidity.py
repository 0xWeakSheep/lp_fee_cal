import numpy as np

# 计算指定价格区间内token0的数量
def get_amount0(sqrtA,sqrtB,liquidity,decimals):
    # 确保sqrtA小于sqrtB
    if (sqrtA > sqrtB):
          (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    # 使用Uniswap V3公式计算token0数量
    amount0=((liquidity*2**96*(sqrtB-sqrtA)/sqrtB/sqrtA)/10**decimals)
    
    return amount0

# 计算指定价格区间内token1的数量
def get_amount1(sqrtA,sqrtB,liquidity,decimals):
    # 确保sqrtA小于sqrtB
    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    # 使用Uniswap V3公式计算token1数量
    amount1=liquidity*(sqrtB-sqrtA)/2**96/10**decimals
    
    return amount1

# 根据当前价格和价格区间计算两种代币的数量
def get_amounts(asqrt,asqrtA,asqrtB,liquidity,decimal0,decimal1):
    # 将价格转换为sqrt价格形式
    sqrt=(np.sqrt(asqrt*10**(decimal1-decimal0)))*(2**96)
    sqrtA=np.sqrt(asqrtA*10**(decimal1-decimal0))*(2**96)
    sqrtB=np.sqrt(asqrtB*10**(decimal1-decimal0))*(2**96)

    # 确保sqrtA小于sqrtB
    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)

    # 根据当前价格在价格区间中的位置计算代币数量
    if sqrt<=sqrtA:
        # 当前价格低于区间
        amount0=get_amount0(sqrtA,sqrtB,liquidity,decimal0)
        return amount0,0
   
    elif sqrt<sqrtB and sqrt>sqrtA:
        # 当前价格在区间内
        amount0=get_amount0(sqrt,sqrtB,liquidity,decimal0)
        amount1=get_amount1(sqrtA,sqrt,liquidity,decimal1)
        return amount0,amount1
    
    else:
        # 当前价格高于区间
        amount1=get_amount1(sqrtA,sqrtB,liquidity,decimal1)
        return 0,amount1      

# 根据代币数量和价格区间计算流动性

# 计算token0对应的流动性
def get_liquidity0(sqrtA,sqrtB,amount0,decimals):
    if (sqrtA > sqrtB):
          (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    # 使用Uniswap V3公式计算流动性
    liquidity=amount0/((2**96*(sqrtB-sqrtA)/sqrtB/sqrtA)/10**decimals)
    return liquidity

# 计算token1对应的流动性
def get_liquidity1(sqrtA,sqrtB,amount1,decimals):
    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    # 使用Uniswap V3公式计算流动性
    liquidity=amount1/((sqrtB-sqrtA)/2**96/10**decimals)
    return liquidity

# 根据当前价格、价格区间和代币数量计算流动性
def get_liquidity(asqrt,asqrtA,asqrtB,amount0,amount1,decimal0,decimal1):
    # 将价格转换为sqrt价格形式
    sqrt=(np.sqrt(asqrt*10**(decimal1-decimal0)))*(2**96)
    sqrtA=np.sqrt(asqrtA*10**(decimal1-decimal0))*(2**96)
    sqrtB=np.sqrt(asqrtB*10**(decimal1-decimal0))*(2**96)

    # 确保sqrtA小于sqrtB
    if (sqrtA > sqrtB):
        (sqrtA,sqrtB)=(sqrtB,sqrtA)
    
    # 根据当前价格在价格区间中的位置计算流动性
    if sqrt<=sqrtA:
        # 当前价格低于区间
        liquidity0=get_liquidity0(sqrtA,sqrtB,amount0,decimal0)
        return liquidity0
    elif sqrt<sqrtB and sqrt>sqrtA:
        # 当前价格在区间内
        liquidity0=get_liquidity0(sqrt,sqrtB,amount0,decimal0)
        liquidity1=get_liquidity1(sqrtA,sqrt,amount1,decimal1)
        # 返回较小的流动性值
        liquidity=liquidity0 if liquidity0<liquidity1 else liquidity1
        return liquidity
    
    else:
        # 当前价格高于区间
        liquidity1=get_liquidity1(sqrtA,sqrtB,amount1,decimal1)
        return liquidity1