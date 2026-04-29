import struct
from typing import override

from opentdx.const import EX_MARKET, MARKET, PERIOD, ADJUST
from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import combine_to_datetime


@register_parser(0x122E, 1)
class SymbolBar(BaseParser):
    def __init__(self, market: MARKET | EX_MARKET, code: str, period: PERIOD, times: int = 1, start: int = 0, count: int = 700, fq: ADJUST = ADJUST.NONE):
        self.body = struct.pack("<H22sHH I HH bbb bH4s", market.value, code.encode("gbk"), period.value, times, start, count, fq.value, 1, 1, 0, 1, 0, b"")
        self.is_ex = isinstance(market, EX_MARKET)

    @override
    def deserialize(self, data):
        row_length = 36
        market, symbol, period, unknow, count, start = struct.unpack("<H12s10xBHHI", data[:33])
        #  4a 00 54 53 4c 41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 03 00 01 0f 00 00 00 00 00

        bars = []
        # print(f"总行数 {row_count}")
        for i in range(count):
            ymd, time_num, open, high, low, close, amount, vol, float_shares = struct.unpack("<II7f", data[33 + i * row_length : 33 + (i + 1) * row_length])

            # 如果是美股或者期货, time_num是中国时间, 但ymd是美国日期. 例如 2026-03-26 22:30:00 的k线, TDX数据返回的是 2026-03-25 22:30:00 
            bars.append({
                "datetime": combine_to_datetime(ymd, time_num, period < 4 or period == 7 or period == 8),
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "vol": vol,
                "amount": amount,
                "float_shares": float_shares,  # 流通股
            })

        return {
            "market": MARKET(market) if not self.is_ex else EX_MARKET(market),
            "code": symbol.decode("gbk").rstrip('\x00'),
            "period": PERIOD(period),
            "count": count,
            "start": start,
            "bars": bars
        }
