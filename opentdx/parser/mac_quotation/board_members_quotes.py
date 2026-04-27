import struct
from typing import override

from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import exchange_board_code
from opentdx.const import MARKET,EX_MARKET, CATEGORY , EX_CATEGORY, SORT_TYPE, SORT_ORDER
from opentdx.utils.log import log
from opentdx.utils.bitmap import FIELD_BITMAP_MAP, QUOTES_DEBUG_ALL_HEX, QUOTES_DEBUG_HEX, BOARD_MEMBERS_QUOTES_DEFAULT_HEX


@register_parser(0x122C, 1)
class BoardMembersQuotes(BaseParser):
    def __init__(
        self,
        board_symbol: str | CATEGORY | EX_CATEGORY = "881001",
        sort_type: int | SORT_TYPE = 0xe,
        start: int = 0,
        page_size: int = 80,
        sort_order: SORT_ORDER = SORT_ORDER.NONE,
        filter: int = 0
    ):
        board_code = exchange_board_code(board_symbol) if isinstance(board_symbol, str) else board_symbol.code
        sort_type_code = sort_type if isinstance(sort_type, int) else sort_type.value

        self.body = struct.pack("<I9xHIBBBB", board_code, sort_type_code, start, page_size, 0, sort_order.value, 0)
        
        if filter == 0:
            # 默认位图：常用字段组合
            bitmap = bytearray.fromhex(BOARD_MEMBERS_QUOTES_DEFAULT_HEX)
        elif filter == -1:
            # 全字段模式（测试用）
            bitmap = bytearray.fromhex(QUOTES_DEBUG_HEX)
        elif filter == -99:
            # 全字段模式（验证新字段使用）
            bitmap = bytearray.fromhex(QUOTES_DEBUG_ALL_HEX)
        else:
            # 根据 filter 整数值生成位图
            bitmap = bytearray(filter.to_bytes(20, 'little'))
        
        self.body = self.body + bitmap

    @override
    def deserialize(self, data):
        field_bitmap = data[:20]  # 前20字节是字段位图
        total, row_count = struct.unpack("<IH", data[20:26])  # 接着是总行数和当前返回行数

        # 检测新字段：对比请求位图和已知字段映射
        known_max_bit = max(FIELD_BITMAP_MAP.keys()) if FIELD_BITMAP_MAP else -1
        for bit_pos in range(known_max_bit + 1, 160):  # 20字节=160位
            if field_bitmap[bit_pos // 8] >> (bit_pos % 8) & 1:
                log.debug(f"[DEBUG] 位图中检测到未知字段 位{bit_pos}，需要分析其含义")
        
        stocks = []
        # 计算每行总长度
        row_len = 68 + 4 * int.from_bytes(field_bitmap, 'little').bit_count()
        for i in range(row_count):
            row_data = data[26 + i * row_len : 26 + (i + 1) * row_len]
            
            market, symbol, name = struct.unpack("<H22s44s", row_data[:68])
            # 目前MARKET 为 0 , 1, 2 
            try:
                market = MARKET(market) if market <= 3 else  EX_MARKET(market)
            except Exception as e:
                print(f"[ERROR] 解析市场信息出错: {e}")
                market = EX_MARKET.TEMP_STOCK

            stock_dict = {
                "market": market,
                "symbol": symbol.decode("gbk", errors="ignore").replace("\x00", ""),
                "name": name.decode("gbk", errors="ignore").replace("\x00", ""),
            }

            index = 0
            for i in range(160):
                if field_bitmap[i // 8] >> (i % 8) & 1:
                    field_name, field_format, _ = FIELD_BITMAP_MAP.get(i, (f"unknown_field_{i}", '<f', "未知字段"))
                    value_bytes = row_data[68 + (index * 4) : 68 + ((index + 1) * 4)]
                    value, = struct.unpack(field_format, value_bytes)
                    if field_name.startswith("unknown_") and field_format == '<f' and value != 0.0 and abs(value) < 1e-6:
                        try:
                            value, = struct.unpack('<i', value_bytes)
                        except Exception:
                            pass
                    log.debug(f"[DEBUG] 解析字段 位{i} -> {field_name}，格式: {field_format}, 数据位置: {68 + (index * 4)}, 原始数据: {value_bytes.hex()}, 解析值: {value}")
                    stock_dict[field_name] = value
                    index += 1

            # 特殊字段处理：格式化 ah_code
            if stock_dict.get("ah_code"):
                market = stock_dict.get("market")
                ah_code_raw = stock_dict.get("ah_code")
                
                # 判断当前股票的市场类型
                if market in [MARKET.SZ, MARKET.SH, MARKET.BJ]:
                    # 国内市场（A股）：ah_code 对应的是港股，需要格式化为5位，不足前面补0
                    stock_dict["ah_code"] = str(ah_code_raw).zfill(5)
                else:
                    # 港股市场：ah_code 对应的是A股，需要格式化为6位，不足前面补0
                    stock_dict["ah_code"] = str(ah_code_raw).zfill(6)
            
            stocks.append(stock_dict)
            
        return {
            "field_bitmap": field_bitmap,
            "count": row_count,
            "total": total,
            "stocks": stocks,
        }