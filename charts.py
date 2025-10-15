import pandas as pd

# 生成回测结果图表和数据分析
def chart1(dpd,base,myliquidity):

    # 根据基准代币计算各项指标的价值
    if base==0:
        # 基准为token0时的计算
        dpd['feeV']= (dpd['myfee0'] )+ (dpd['myfee1']* dpd['close']) # 手续费总价值
        dpd['amountV']= (dpd['amount0'] ) + (dpd['amount1']* dpd['close']) # 流动性总价值
        dpd['amountunb']= (dpd['amount0unb'] )+ (dpd['amount1unb']* dpd['close']) # 未绑定流动性价值
        dpd['fgV']= (dpd['fee0token'])+ (dpd['fee1token']* dpd['close']) # 全局手续费价值
        dpd['feeusd']= dpd['feeV'] * (dpd['pool.totalValueLockedUSD'].iloc[0] / (dpd['pool.totalValueLockedToken1'].iloc[0]* dpd['close'].iloc[0]+(dpd['pool.totalValueLockedToken0'].iloc[0]))) # USD计价手续费

    else:
        # 基准为token1时的计算
        dpd['feeV']= (dpd['myfee0'] / dpd['close']) + dpd['myfee1']
        dpd['amountV']= (dpd['amount0'] / dpd['close'])+ dpd['amount1']
        dpd['feeVbase0']= dpd['myfee0'] + (dpd['myfee1']* dpd['close'])
        dpd['amountunb']= (dpd['amount0unb'] / dpd['close'])+ dpd['amount1unb']
        dpd['fgV']=(dpd['fee0token'] / dpd['close'])+ dpd['fee1token']
        dpd['feeusd']= dpd['feeV'] * ( dpd['pool.totalValueLockedUSD'].iloc[0] / (dpd['pool.totalValueLockedToken1'].iloc[0] + (dpd['pool.totalValueLockedToken0'].iloc[0]/dpd['close'].iloc[0])))

    # 转换时间戳为日期格式
    dpd['date']=pd.to_datetime(dpd['periodStartUnix'],unit='s')

    # 提取需要的数据列
    data=dpd[['date','myfee0','myfee1','fgV','feeV','feeusd','amountV','ActiveLiq','amountunb','amount0','amount1','close']]
    data=data.fillna(0) # 填充空值

    # 按日期重采样数据
    temp =  data.resample('D',on='date').sum() # 计算每日累计值
    final1=temp[['myfee0','myfee1','feeV','fgV','feeusd']].copy()

    temp2 = data.resample('D',on='date').mean() # 计算每日平均值
    final1['ActiveLiq']=temp2['ActiveLiq'].copy()
    
    temp3 = data.resample('D',on='date').first() # 获取每日首个值
    final1[['amountV','amountunb']]=temp3[['amountV','amountunb']].copy()
    temp4 = data.resample('D',on='date').last() # 获取每日最后值
    final1[['amountVlast']]=temp4[['amountV']]

    # 计算收益率指标
    final1['S1%']=final1['feeV']/final1['amountV']*100 # 策略收益率
    final1['unb%']=final1['fgV']/final1['amountunb']*100 # 未绑定策略收益率
    final1['multiplier']=final1['S1%']/final1['unb%'] # 收益倍数
    final1['feeunb'] = final1['amountV']*final1['unb%']/100 # 未绑定手续费
    
    # 保存数据到CSV
    final1.to_csv("chart1.csv",sep = ";")
    
    # 打印主要指标
    print(final1[['feeunb','feeV','feeusd','amountV','ActiveLiq','S1%','unb%','ActiveLiq']])

    # 打印回测结果统计
    print('------------------------------------------------------------------')
    print("this position returned", final1['feeV'].sum()/final1['amountV'].iloc[0]*100,"in ",len(final1.index)," days, for an apr of ",final1['feeV'].sum()/final1['amountV'].iloc[0]*365/len(final1.index)*100)
    print("a base  position returned", final1['feeunb'].sum()/final1['amountV'].iloc[0]*100,"in ",len(final1.index)," days, for an apr of ",final1['feeunb'].sum()/final1['amountV'].iloc[0]*365/len(final1.index)*100)
    
    # 打印手续费统计
    print ("fee in token 1 and token 2",dpd['myfee0'].sum(),dpd['myfee1'].sum() )
    print("totalFee in USD", final1['feeusd'].sum())
    print ('Your liquidity was active for:',final1['ActiveLiq'].mean())
    forecast= (dpd['feeVbase0'].sum()*myliquidity*final1['ActiveLiq'].mean())
    print('forecast: ',forecast)
    print('------------------------------------------------------------------')

    # 生成第二个图表的数据
    final2=temp3[['amountV','amount0','amount1','close']].copy()
    final2['feeV']=temp['feeV'].copy()
    final2[['amountVlast']]=temp4[['amountV']]

    # 计算HODL策略收益
    final2['HODL']=final2['amount0'].iloc[0] / final2['close'] + final2['amount1'].iloc[0]
    
    # 计算无常损失和收益指标
    final2['IL']=final2['amountVlast']- final2['HODL'] # 无常损失
    final2['ActiveLiq']=temp2['ActiveLiq'].copy()
    final2['feecumsum']=final2['feeV'].cumsum() # 累计手续费
    final2 ['PNL']= final2['feecumsum'] + final2['IL'] # 总盈亏

    # 计算归一化指标
    final2['HODLnorm']=final2['HODL']/final2['amountV'].iloc[0]*100
    final2['ILnorm']=final2['IL']/final2['amountV'].iloc[0]*100
    final2['PNLnorm']=final2['PNL']/final2['amountV'].iloc[0]*100
    final2['feecumsumnorm'] = final2['feecumsum']/final2['amountV'].iloc[0]*100
    
    # 保存数据到CSV
    final2.to_csv("chart2.csv",sep = ";")
    
    # 打印图表数据
    ch2=final2[['amountV','feecumsum']]
    ch3=final2[['ILnorm','PNLnorm','feecumsumnorm']]
    print(ch2)
    print(ch3)

    # 生成第三个图表的数据
    final3=pd.DataFrame()
    final3['amountV']=data['amountV']
    final3['amountVlast']=data['amountV'].shift(-1)
    final3['date']=data['date']
    final3['HODL']=data['amount0'].iloc[0] / data['close'] + data['amount1'].iloc[0]

    # 计算详细的收益指标
    final3['amountVlast'].iloc[-1]=final3['HODL'].iloc[-1]
    final3['IL']=final3['amountVlast']- final3['HODL']
    final3['feecumsum']=data['feeV'][::-1].cumsum()
    final3 ['PNL']= final3['feecumsum'] + final3['IL']
    final3['HODLnorm']=final3['HODL']/final3['amountV'].iloc[0]*100
    final3['ILnorm']=final3['IL']/final3['amountV'].iloc[0]*100
    final3['PNLnorm']=final3['PNL']/final3['amountV'].iloc[0]*100
    final3['feecumsumnorm'] = final3['feecumsum']/final3['amountV'].iloc[0]*100

    # 打印最终结果
    ch2=final3[['amountV','feecumsum']]
    ch3=final3[['ILnorm','PNLnorm','feecumsumnorm']]
    print(ch2)
    print(ch3)



   
    
   

    

    