from datetime import datetime, timezone
from typing import Optional

from gql import Client, gql
try:
    from gql.transport.requests import RequestsHTTPTransport
except ModuleNotFoundError as exc:  # pragma: no cover - import side effect guard
    raise ModuleNotFoundError(
        "缺少依赖 requests-toolbelt；请先运行 `pip install requests-toolbelt` 后重试。"
    ) from exc
import pandas as pd
from GetFeeGrowthGolbalFromBlock import fetch_pool_series_by_blockday, fetch_pool_data

# 从不同网络的Uniswap V3 Graph获取池子数据（仅每小时）
def graph(network, Adress, fromdate, todate: Optional[int] = None):
    # 根据网络选择正确的端点
    if network == 1:  # Ethereum
        endpoint = "https://gateway.thegraph.com/api/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    elif network == 2:  # Arbitrum
        endpoint = "https://gateway.thegraph.com/api/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    elif network == 3:  # Optimism
        endpoint = "https://gateway.thegraph.com/api/subgraphs/id/Cghf4LfVqPiFw6fp6Y5X5Ubc8UpmUhSfJL82zwiBFLaj"
    else:
        raise ValueError("不支持的网络")
    
    # 所有网络都需要认证头
    headers = {
        "Authorization": "Bearer ce9117e26e254f69e91a2accfeb01d2f"
    }
    
    # 使用带认证的传输
    sample_transport = RequestsHTTPTransport(
        url=endpoint,
        headers=headers,
        verify=True,
        retries=5,
    )
    
    client = Client(
        transport=sample_transport
    )
    
    print(fromdate)

    # 仅每小时路径：构建分页查询
    def build_where_conditions(fromdate, todate, last_ts=None, last_id=None):
        # 动态构建 where 条件，避免传 null
        conditions = [f'pool:"{str(Adress)}"', f'periodStartUnix_gt:{fromdate}']
        if todate is not None:
            conditions.append(f'periodStartUnix_lte:{todate}')
        if last_ts is not None:
            conditions.append(f'periodStartUnix_lt:{last_ts}')
        if last_id is not None:
            conditions.append(f'id_gt:"{last_id}"')
        return ','.join(conditions)
    
    def build_query_variables(fromdate, todate, last_ts=None, last_id=None):
        variables = {"fromdate": fromdate}
        if todate is not None:
            variables["todate"] = todate
        if last_ts is not None:
            variables["lastTs"] = last_ts
        if last_id is not None:
            variables["lastId"] = last_id
        return variables
    
    def format_timestamp(value: str) -> str:
        """将 Unix 时间戳转换为可读的 UTC 时间，如果失败则返回原值。"""
        try:
            return datetime.utcfromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, TypeError, OSError):
            return value

    def human_readable_where(where_conditions: str) -> str:
        """把 where_conditions 字符串转换为更容易理解的中文描述。"""
        readable_parts = []
        for part in where_conditions.split(','):
            stripped = part.strip()
            if not stripped:
                continue

            key, _, raw_value = stripped.partition(':')
            value = raw_value.strip('"')

            if key == 'pool':
                readable_parts.append(f"池子地址 = {value}")
            elif key == 'periodStartUnix_gt':
                readable_parts.append(
                    f"起始时间 > {value} ({format_timestamp(value)})"
                )
            elif key == 'periodStartUnix_lte':
                readable_parts.append(
                    f"结束时间 ≤ {value} ({format_timestamp(value)})"
                )
            elif key == 'periodStartUnix_lt':
                readable_parts.append(
                    f"分页上限时间 < {value} ({format_timestamp(value)})"
                )
            elif key == 'id_gt':
                readable_parts.append(f"分页使用的上一条记录 ID > {value}")
            else:
                readable_parts.append(stripped)

        return '；'.join(readable_parts) if readable_parts else where_conditions

    def build_graphql_query(where_conditions, has_todate, has_last_ts, has_last_id):
        var_declarations = ["$fromdate: Int!"]
        if has_todate:
            var_declarations.append("$todate: Int")
        if has_last_ts:
            var_declarations.append("$lastTs: Int")
        if has_last_id:
            var_declarations.append("$lastId: String")
       
        query_str = f'''
        query ({', '.join(var_declarations)})
        {{
        poolHourDatas(where:{{{where_conditions}}},orderBy:periodStartUnix,orderDirection:desc,first:1000)
        {{
        id
        periodStartUnix
        liquidity
        high
        low
        pool{{
            totalValueLockedUSD
            totalValueLockedToken1
            totalValueLockedToken0
            token0
                {{decimals}}
            token1
                {{decimals}}
            }}
        close

        }}
        }}
        '''
        print("GraphQL 查询条件:", human_readable_where(where_conditions))
        #<要求2>使用where_conditions里的时间戳数据和池子数据，去使用GetFeeGrowthGolbalFromBlock.py里面的fetch_pool_series_by_blockday函数，找到对应的feeGrowthGlobal0X128和feeGrowthGlobal1X128
        #<提示2>删除原本查询语句里面的feeGrowthGlobal0X128和feeGrowthGlobal1X128，并且我希望在返回结果里面，保持原本的状态（包括字段），但是值用新的替换，目的是为了小程度修改代码，使得代码维护性提高
        #在这里下面做修改
        nonlocal fee_growth_updater
        query_str = query_str.replace('\n        feeGrowthGlobal0X128\n        feeGrowthGlobal1X128', '')
        def fee_growth_updater(records, cache={}, state={'base_ts': None, 'base_block': None}):
            if not records:
                return
            blocks_per_hour = 14400
            for record in records:
                try:
                    timestamp = int(record.get('periodStartUnix'))
                except (TypeError, ValueError):
                    record['feeGrowthGlobal0X128'] = None
                    record['feeGrowthGlobal1X128'] = None
                    continue

                if timestamp not in cache:
                    if state['base_ts'] is None:
                        series = fetch_pool_series_by_blockday(timestamp, timestamp, blockday=1, pool_id=Adress)
                        last = series[-1] if series else None
                        fg0 = last.get('feeGrowthGlobal0X128') if last else None
                        fg1 = last.get('feeGrowthGlobal1X128') if last else None
                        cache[timestamp] = (fg0, fg1)
                        state['base_ts'] = timestamp
                        state['base_block'] = last.get('blockNumber') if last else None
                    else:
                        base_ts = state['base_ts']
                        base_block = state['base_block']
                        if base_block is None:
                            cache[timestamp] = (None, None)
                        else:
                            delta_seconds = timestamp - base_ts
                            hours_diff = abs(delta_seconds) // 3600
                            block_offset = int(hours_diff) * blocks_per_hour
                            if delta_seconds < 0:
                                approx_block = max(0, base_block - block_offset)
                            else:
                                approx_block = base_block + block_offset
                            snapshot = fetch_pool_data(Adress, approx_block)
                            if snapshot:
                                fg0 = snapshot.get('feeGrowthGlobal0X128')
                                fg1 = snapshot.get('feeGrowthGlobal1X128')
                                cache[timestamp] = (fg0, fg1)
                                state['base_ts'] = timestamp
                                state['base_block'] = approx_block
                            else:
                                cache[timestamp] = (None, None)

                fg0, fg1 = cache.get(timestamp, (None, None))
                record['feeGrowthGlobal0X128'] = fg0
                record['feeGrowthGlobal1X128'] = fg1
        return gql(query_str)
    
    # 分页获取所有数据
    all_data = []
    last_ts = None
    last_id = None
    page_count = 0
    fee_growth_updater = lambda records: None
    
    while True:
        where_conditions = build_where_conditions(fromdate, todate, last_ts, last_id)
        has_todate = todate is not None
        has_last_ts = last_ts is not None
        has_last_id = last_id is not None
        query = build_graphql_query(where_conditions, has_todate, has_last_ts, has_last_id)
        params = build_query_variables(fromdate, todate, last_ts, last_id)

        try:
            if page_count == 0:
                print(f"正在查询网络: {network}")
                print(f"使用端点: {endpoint}")
                print(f"正在查询地址: {Adress}")
                print(f"查询时间范围: {fromdate} - {todate if todate else '最新'}")
            
            response = client.execute(query, variable_values=params)
            batch_data = response.get('poolHourDatas', [])
            if not batch_data:
                print("没有更多数据，结束分页")
                break
                
            fee_growth_updater(batch_data)

            all_data.extend(batch_data)
            page_count += 1
            last_ts = batch_data[-1]['periodStartUnix']
            last_id = batch_data[-1]['id']
            print(f"已获取第 {page_count} 页，本页 {len(batch_data)} 条数据，累计 {len(all_data)} 条")
            if len(batch_data) < 1000:
                print("已获取所有数据")
                break
                
        except Exception as e:
            print(f"查询执行错误: {str(e)}")
            print(f"当前分页参数: last_ts={last_ts}, last_id={last_id}")
            print(f"查询变量: {params}")
            raise
    
    # 处理所有数据
    if not all_data:
        pool_query = gql('''
        query {
            pool(id: "''' + str(Adress) + '''") {
                id
                createdAtTimestamp
            }
        }
        ''')
        pool_info = client.execute(pool_query)
        print("池子信息:", pool_info)
        raise ValueError(f"未获取到数据。\n"
                       f"地址: {Adress}\n"
                       f"时间范围: {fromdate} - {todate if todate else '最新'}\n"
                       f"请确认:\n"
                       f"1. 池子地址是否正确\n"
                       f"2. 时间戳是否在池子创建时间之后\n"
                       f"3. 是否有该时间段的数据")
    
    dpd = pd.json_normalize(all_data)
    print(f"总共获取到 {len(dpd)} 条数据")
    print("数据列：", dpd.columns.tolist())
    
    # 按时间戳排序（从旧到新）
    dpd = dpd.sort_values('periodStartUnix').reset_index(drop=True)
    
    # 排除 id 列，只转换其他列
    columns_to_convert = [col for col in dpd.columns if col != 'id']
    dpd[columns_to_convert] = dpd[columns_to_convert].astype(float)
    print(f"已转换列: {columns_to_convert}")

    return dpd


def example_usage(run_query: bool = False):
    """展示如何调用 graph 函数，可选是否真正发出网络请求。"""
    example_network = 1  # 1 表示以太坊主网
    example_pool_address = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"  # USDC/WETH 0.3% 池子
    example_fromdate = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
    example_todate = int(datetime(2024, 1, 3, tzinfo=timezone.utc).timestamp())

    print("示例参数:")
    print(f"  network = {example_network}")
    print(f"  pool address = {example_pool_address}")
    print(f"  fromdate = {example_fromdate} (UTC 2024-01-01 00:00:00)")
    print(f"  todate = {example_todate} (UTC 2024-01-03 00:00:00)")

    if not run_query:
        print("仅展示参数，未真正请求。设定 run_query=True 可以拉取数据。")
        return None

    df = graph(example_network, example_pool_address, example_fromdate, example_todate)
    print("示例数据前 5 行:")
    print(df.head())
    return df


if __name__ == "__main__":
    example_usage(run_query=False)
