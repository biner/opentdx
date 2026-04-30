from datetime import date, time
import struct
from opentdx.const import MARKET, EX_MARKET
from opentdx.parser.baseParser import BaseParser, register_parser


@register_parser(0x123E, 1)
class TickCharts(BaseParser):
    def __init__(self, market: MARKET | EX_MARKET, code: str, query_date: date = None, days: int = 5):
        self.is_ex = isinstance(market, EX_MARKET)
        start_day = query_date.year * 10000 + query_date.month * 100 + query_date.day if query_date else 0
        self.body = struct.pack('<H22sIHH6x', market.value, code.encode('gbk'), start_day, days, 1)

    def deserialize(self, data):
        market, code = struct.unpack_from('<H22s', data, 0)

        try:
            market = MARKET(market) if not self.is_ex else EX_MARKET(market)
        except Exception:
            pass

        pre_closes = struct.unpack_from('<5I5f', data, 24)
                #透传最后那个值，没看出意义来
        count, send_last, page_size, total = struct.unpack_from('<HBHH', data, 64)

        charts = []
        for d in range(count):
            ticks = []
            for t in range(page_size):
                index = d * page_size + t
                minutes, price, avg, vol, _  = struct.unpack_from('<HffHH', data, 71 + index * 14)
                
                ticks.append({
                    'minutes': time(minutes // 60, minutes % 60),
                    'price': price,
                    'avg': avg,
                    'vol': vol
                })
            charts.append({
                'date': date(pre_closes[d] // 10000, (pre_closes[d] % 10000) // 100, pre_closes[d] % 100),
                'pre_close': pre_closes[d + 5],
                'ticks': ticks
            })

        # c6bdb0b2d2f8d0d00000000000000000000000000000000000000000000000000000000000000000000000000200000000c8420000000000
        # 4e263501 e956 0200 ec513841 00003841 9a993941 295c3741 0ad73741 0000000029621100 53809c4e 000000000000000000000000194a163f 12613841 094c0100
        print(data[71 + count * page_size * 14:].hex())

        return {
            'market': market,
            'code': code.decode('gbk').rstrip('\x00'),
            'charts': charts
        }
