import struct
from opentdx._typing import override

from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.const import CATEGORY, EX_CATEGORY, MARKET,EX_MARKET, SORT_ORDER, SORT_TYPE
from opentdx.utils.help import exchange_board_code


@register_parser(0x122C, 1)
class BoardMembers(BaseParser):
    def __init__(
        self,
        board_symbol: str | CATEGORY | EX_CATEGORY = "881001",
        sort_type: int | SORT_TYPE = 0xe,
        start: int = 0,
        page_size: int = 80,
        sort_order: SORT_ORDER = SORT_ORDER.NONE
    ):
        
        board_code = exchange_board_code(board_symbol) if isinstance(board_symbol, str) else board_symbol.code
        sort_type_code = sort_type if isinstance(sort_type, int) else sort_type.value
        
        self.body = struct.pack("<I9xHIBBBB", board_code, sort_type_code, start, page_size, 0, sort_order.value, 0)
        
        # 位图配置：20字节，每一位代表一个字段是否存在
        # 全传0, 只查板块的成员,通过 board_members 查询
        bitmap = bytearray(20)
        
        self.body = self.body + bitmap

    @override
    def deserialize(self, data):
        field_bitmap = data[:20]  # 前20字节是字段位图
        total, row_count = struct.unpack("<IH", data[20:26])  # 接着是总行数和当前返回行数

        stocks = []
        for i in range(row_count):
            row_data = data[26 + i * 68 : 26 + (i + 1) * 68]

            market, symbol, name = struct.unpack("<H22s44s", row_data[:68])
            # 目前MARKET 为 0 , 1, 2 
            try:
                market = MARKET(market) if market <= 3 else  EX_MARKET(market)
            except Exception as e:
                print(f"[ERROR] 解析市场信息出错: {e}")
                market = EX_MARKET.TEMP_STOCK

            stocks.append({
                "market": market,
                "symbol": symbol.decode("gbk", errors="ignore").replace("\x00", ""),
                "name": name.decode("gbk", errors="ignore").replace("\x00", ""),
            })

        result = {
            "field_bitmap": field_bitmap,
            "count": row_count,
            "total": total,
            "stocks": stocks,
        }
        return result
