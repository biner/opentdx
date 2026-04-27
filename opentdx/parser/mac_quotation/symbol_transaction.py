from datetime import time,date
import struct
from typing import Union

from opentdx.const import EX_MARKET, MARKET
from opentdx.parser.baseParser import BaseParser, register_parser


def seconds_to_time_str(secs: int) -> str:
    """将从0点开始的秒数转换为 HH:MM:SS"""
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

@register_parser(0x122F, 1)
class SymbolTransaction(BaseParser):
    """
    股票逐笔成交解析器 (命令字: 0x122F)
    
    用于获取股票的逐笔成交明细数据
    """
    
    def __init__(self, market: Union[MARKET, EX_MARKET], symbol: str,   count: int = 1000, start: int = 0, query_date : date = None ):
        """
        初始化逐笔成交查询

        Args:
            market: 市场代码 (MARKET 或 EX_MARKET 枚举)
            code: 股票代码字符串
            start: 起始位置 (默认0)
            count: 查询笔数 (默认10)


        TCPDUMP 请求示例：
        0x0040:  0100 3638 3833 3831 0000 0000 0000 0000  ..688381........
        0x0050:  0000 0000 0000 0000 0000 0000 0000 0000  ................
	    0x0060:  3200 0100 0000 0000 0000 0000            2...........                      ....
        """
        if query_date is not None:
            ymd = int(query_date.strftime("%Y%m%d"))
        else:
            ymd = 0
        self.body = struct.pack("<H22s I I H 10x",
                                market.value,
                                symbol.encode("gbk"),
                                ymd,      # unknown1
                                start,      # unknown2
                                count

                                )
        print(self.body.hex())
    def deserialize(self, data):
        """
        解析逐笔成交数据
        
        Args:
            data: 二进制响应数据
            
        Returns:
            dict: 包含市场、代码和逐笔成交列表的字典
        """
        # 首先解析头部信息
        # 根据抓包数据和类似协议推断头部结构
        print(data[:39].hex())
        market, symbol_raw, query_date, count, start, total = struct.unpack(
            "<H22sIxHII", data[:39]
        )
        print(market, symbol_raw, query_date, count,start, total )
        
        market, symbol_raw = struct.unpack("<H22s", data[:24])
        symbol = symbol_raw.decode("gbk", errors="ignore").replace('\x00', '')


        transactions = []
            
        RECORD_SIZE = 18
            
        for i in range(count):
            off = 39 + i * RECORD_SIZE
            record = data[off:off+RECORD_SIZE]
            if len(record) < RECORD_SIZE:
                break
            time_sec, price, volume, trade_count, bs_flag  = struct.unpack("<I f I I H", record)
            # bs_flag 0=买入，1=卖出，2=中性盘  5=盘后
            transactions.append({
                "time": seconds_to_time_str(time_sec),   # 转换为 HH:MM:00
                "price": round(price, 3),
                "volume": volume,
                "trade_count": trade_count,
                "bs_flag ": bs_flag 
            })
        

        return {
            "data": data,
            "market": market,
            "symbol": symbol,
            "query_date": query_date,
            "count": count,
            "start": start,
            "total": total,
            "transactions": transactions
        }
