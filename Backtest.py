# 导入必要的库
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
import matplotlib.dates as mdates
import numpy as np
import liquidity
import GraphBacktest
import charts

# 网络选择: 1=以太坊主网, 2=Arbitrum, 3=Optimism
network = 1  # Ethereum 主网

# 各种池子地址
Adress = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # USDC/ETH 主网池子

# 方式2：使用日期字符串（自动转换为时间戳）
from datetime import datetime, timezone
start_date = "2025-10-11"  # 开始日期
end_date = "2025-10-14"    # 结束日期

# 将日期字符串转换为UTC时间戳（确保时区一致）
start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
startfrom = int(start_dt.timestamp())
endto = int(end_dt.timestamp())

print(f"回测时间范围: {start_date} 到 {end_date}")
print(f"对应时间戳: {startfrom} 到 {endto}")
print(f"开始时间: {start_dt}")
print(f"结束时间: {end_dt}")

print(f"使用每小时精度获取数据，时间范围: {start_date} 到 {end_date}")
dpd = GraphBacktest.graph(network, Adress, startfrom, todate=endto)

# 获取代币精度信息       
decimal0 = dpd.iloc[0]['pool.token0.decimals']  # token0 精度
decimal1 = dpd.iloc[0]['pool.token1.decimals']  # token1 精度
decimal = decimal1-decimal0  # 精度差值

# 计算全局手续费增长
# 将128位定点数转换为标准数值，并根据代币精度进行调整
dpd['fg0'] = ((dpd['feeGrowthGlobal0X128'])/(2**128))/(10**decimal0)
dpd['fg1'] = ((dpd['feeGrowthGlobal1X128'])/(2**128))/(10**decimal1)

# 设置流动性价格区间参数
mini = 3471  # 最小价格边界
maxi = 4243  # 最大价格边界
target = 10000  # 目标流动性价值
base = 0  # 基准代币选择: 0=token0, 1=token1

# 计算每期的手续费增长（修正版本）
dpd['fg0shift'] = dpd['fg0'].shift(1)  # 上一期的手续费
dpd['fg1shift'] = dpd['fg1'].shift(1)
dpd['fee0token'] = dpd['fg0'] - dpd['fg0shift']  # 当期手续费增长 = 当前期 - 上一期
dpd['fee1token'] = dpd['fg1'] - dpd['fg1shift']

# 处理第一行数据（没有上一期数据，设为0）
dpd['fee0token'] = dpd['fee0token'].fillna(0)
dpd['fee1token'] = dpd['fee1token'].fillna(0)

# 确保手续费增长不为负数（手续费增长应该是累积的，不应该减少）
dpd['fee0token'] = dpd['fee0token'].clip(lower=0)
dpd['fee1token'] = dpd['fee1token'].clip(lower=0)
# 计算流动性相关参数
SMIN = np.sqrt(mini * 10 ** (decimal))   # 最小价格的平方根
SMAX = np.sqrt(maxi * 10 ** (decimal))   # 最大价格的平方根

# 根据基准代币计算初始价格
if base == 0:
    sqrt0 = np.sqrt(dpd['close'].iloc[-1] * 10 ** (decimal))
    dpd['price0'] = dpd['close']
else:
    sqrt0 = np.sqrt(1/dpd['close'].iloc[-1] * 10 ** (decimal))
    dpd['price0'] = 1/dpd['close']

# 根据当前价格位置计算所需的token数量
if sqrt0 > SMIN and sqrt0 < SMAX:
    # 价格在区间内
    deltaL = target / ((sqrt0 - SMIN) + (((1 / sqrt0) - (1 / SMAX)) * (dpd['price0'].iloc[-1] * 10 ** (decimal))))
    amount1 = deltaL * (sqrt0-SMIN)
    amount0 = deltaL * ((1/sqrt0)-(1/SMAX)) * 10 ** (decimal)
elif sqrt0 < SMIN:
    # 价格低于区间
    deltaL = target / (((1 / SMIN) - (1 / SMAX)) * (dpd['price0'].iloc[-1]))
    amount1 = 0
    amount0 = deltaL * ((1/SMIN) - (1/SMAX))
else:
    # 价格高于区间
    deltaL = target / (SMAX-SMIN)
    amount1 = deltaL * (SMAX-SMIN)
    amount0 = 0

print("Amounts:", amount0, amount1)

# 计算流动性
myliquidity = liquidity.get_liquidity(dpd['price0'].iloc[-1], mini, maxi, amount0, amount1, decimal0, decimal1)
print("OK myliquidity", myliquidity)

# 初始化流动性统计数据
dpd['ActiveLiq'] = 0  # 活跃流动性比例
dpd['amount0'] = 0    # token0 数量
dpd['amount1'] = 0    # token1 数量
dpd['amount0unb'] = 0 # 无限区间 token0 数量
dpd['amount1unb'] = 0 # 无限区间 token1 数量

# 根据基准代币计算每期的流动性状态
if base == 0:  # 如果使用token0作为基准代币
    for i, row in dpd.iterrows():
        # 计算价格区间内的活跃流动性比例
        # 判断当前价格是否与设定的价格区间有重叠
        if dpd['high'].iloc[i] > mini and dpd['low'].iloc[i] < maxi:
            # 计算重叠区间占总价格区间的比例
            # min(maxi,high): 取重叠区间的上界
            # max(low,mini): 取重叠区间的下界
            # 相减得到重叠区间长度，除以总区间长度，转换为百分比
            dpd.iloc[i,dpd.columns.get_loc('ActiveLiq')] = (min(maxi,dpd['high'].iloc[i]) - max(dpd['low'].iloc[i],mini)) / (dpd['high'].iloc[i]-dpd['low'].iloc[i]) * 100
        else:
            # 如果价格完全在区间外，活跃流动性为0
            dpd.iloc[i,dpd.columns.get_loc('ActiveLiq')] = 0
        
        # 计算有限价格区间的token数量
        # 根据当前价格、设定的价格区间和流动性计算应持有的token数量
        amounts = liquidity.get_amounts(dpd['price0'].iloc[i], mini, maxi, myliquidity, decimal0, decimal1)
        dpd.iloc[i,dpd.columns.get_loc('amount0')] = amounts[1]  # token0数量
        dpd.iloc[i,dpd.columns.get_loc('amount1')] = amounts[0]  # token1数量
        
        # 计算无限价格区间的token数量（用于比较基准情况）
        # 1.0001**(-887220)和1.0001**887220是最小和最大可能的价格
        # 相当于在整个价格范围内提供流动性
        amountsunb = liquidity.get_amounts((dpd['price0'].iloc[i]), 1.0001**(-887220), 1.0001**887220, 1, decimal0, decimal1)
        dpd.iloc[i,dpd.columns.get_loc('amount0unb')] = amountsunb[1]  # 无限区间token0数量
        dpd.iloc[i,dpd.columns.get_loc('amount1unb')] = amountsunb[0]  # 无限区间token1数量

# 计算最终的手续费收入
dpd['myfee0'] = dpd['fee0token'] * myliquidity * dpd['ActiveLiq'] / 100  # token0 手续费
dpd['myfee1'] = dpd['fee1token'] * myliquidity * dpd['ActiveLiq'] / 100  # token1 手续费

# 添加基准手续费计算
dpd['feeVbase0'] = dpd['fee0token']  # token0 基准手续费
dpd['feeVbase1'] = dpd['fee1token']  # token1 基准手续费

# 生成图表
a = charts.chart1(dpd, base, myliquidity)

# =============================
# 使用说明
# =============================
# 
# 1. 时间范围设置：
#    - 方式1：直接使用时间戳 (startfrom, endto)
#    - 方式2：使用日期字符串 (start_date, end_date) - 推荐
#    - 支持任意时间范围，不再限制为45天
#    - 自动分页获取所有历史数据
#
# 2. 每小时精度 (granularity='1h')：
#    - 获取完整的池子数据：价格OHLC、流动性、费增长等
#    - 适合长期回测和策略分析
#    - 支持任意时间范围，自动分页
#    - 数据量适中，处理速度快
#
# 3. 5分钟精度 (granularity='5m')：
#    - 获取高精度的费增长增量数据
#    - 价格OHLC数据仍使用每小时精度（需要额外数据源补充）
#    - 适合短期高频策略分析
#    - 数据量大，建议设置合理的时间范围
#
# 4. 数据获取改进：
#    - 解决了只能获取45天数据的限制
#    - 支持分页获取完整历史数据
#    - 自动处理时间范围查询
#    - 更好的错误提示和数据验证
#
# 5. 如需完整的5分钟价格数据，可以考虑：
#    - 使用其他价格API（如CoinGecko、Binance等）
#    - 基于swaps事件聚合生成5分钟OHLC
#    - 结合多个数据源进行回测
#
# 6. 当前实现将5分钟费增长数据聚合为小时级别，与价格数据合并
#    这样可以保持现有回测逻辑不变，同时获得更精确的费增长计算