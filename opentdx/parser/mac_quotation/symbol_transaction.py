from datetime import date, time
import struct
from typing import Union

from opentdx.const import EX_MARKET, MARKET
from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import seconds_to_time_str

@register_parser(0x122F, 1)
class SymbolTransaction(BaseParser):
    def __init__(self, market: Union[MARKET, EX_MARKET], code: str, count: int = 1000, start: int = 0, query_date : date = None):
        ymd = query_date.year * 10000 + query_date.month * 100 + query_date.day if query_date else 0
        self.body = struct.pack("<H22sIIH10x", market.value, code.encode("gbk"), ymd, start, count)

    def deserialize(self, data):
        # 首先解析头部信息
        # 根据抓包数据和类似协议推断头部结构
        # print(data[:39].hex())
        market, code, query_date, count, start, total = struct.unpack("<H22sIxHII", data[:39])

        transactions = []
        for i in range(count):
            time_sec, price, volume, trade_count, bs_flag  = struct.unpack("<IfIIH", data[39 + i * 18 :39 + i * 18 + 18])
            # bs_flag 0=买入，1=卖出，2=中性盘  5=盘后
            transactions.append({
                "time": time(time_sec // 3600, time_sec % 3600 // 60, time_sec % 60),   # 转换为 HH:MM:00
                "price": price,
                "volume": volume,
                "trade_count": trade_count,
                "bs_flag ": bs_flag 
            })
        

        return {
            "market": market,
            "code": code.decode("gbk", errors="ignore").replace('\x00', ''),
            "query_date": query_date,
            "count": count,
            "start": start,
            "total": total,
            "transactions": transactions
        }
