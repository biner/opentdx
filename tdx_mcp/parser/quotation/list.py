import struct
from typing import override

from tdx_mcp.const import MARKET
from tdx_mcp.parser.baseParser import BaseParser, register_parser


def hex_to_price(hex_str):
    actual = struct.unpack('<f', bytes.fromhex(hex_str))[0]
    return actual

@register_parser(0x44d) # TODO: 2Unknown
class List(BaseParser):
    def __init__(self, market: MARKET, start: int = 0, count: int = 1600):
        self.body = struct.pack(u'<H3I', market.value, start, count, 0)

    @override
    def deserialize(self, data):
        count, = struct.unpack('<H', data[:2])
        
        stocks = []
        for i in range(count):
            pos = 2 + i * 37
            code, vol, name, unknown1, decimal_point, pre_close, unknown2 = struct.unpack('<6sH16s4sBf4s', data[pos: pos + 37])

            # print(name.decode('gbk', errors='ignore').rstrip('\x00'), unknown1, unknown2, unknown3)
            # print(data[pos: pos + 37].hex())
            stocks.append({
                'code': code.decode('gbk', errors='ignore').rstrip('\x00'),
                'vol': vol,
                'name': name.decode('gbk', errors='ignore').rstrip('\x00'),
                'decimal_point': decimal_point,
                'pre_close': pre_close,
                'unknown1': unknown1.hex(),
                # 'debug': hex_to_price(unknown1.hex()),
                'unknown2': unknown2.hex(),
            })

        return stocks