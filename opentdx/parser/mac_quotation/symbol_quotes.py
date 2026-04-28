import struct
from typing import List, Tuple

from opentdx._typing import override
from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.const import MARKET, EX_MARKET
from opentdx.utils.log import log
from opentdx.utils.bitmap import FIELD_BITMAP_MAP, SYMBOL_QUOTES_DEFAULT_HEX, QUOTES_DEBUG_HEX, QUOTES_DEBUG_ALL_HEX, FieldBit, PresetField
@register_parser(0x122B, 1)
class SymbolQuotes(BaseParser):
    
    def __init__(self, code_list: List[Tuple[MARKET | EX_MARKET, str]], fields: list[FieldBit] | PresetField = PresetField.COMMON):
        if isinstance(fields, PresetField):
            fields = fields.value
            
        bit_fields = [field.value for field in fields]
        bitmap = bytearray(20)
        for bit in bit_fields:
            byte_index = bit // 8
            bit_index = bit % 8
            bitmap[byte_index] |= (1 << bit_index)
        
        self.body = bitmap + struct.pack('H', len(code_list))
        for market, code in code_list:
            self.body.extend(struct.pack('<H22s', market.value, code.encode('gbk')))

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
        quotes_field_count = int.from_bytes(field_bitmap, 'little').bit_count()
        row_len = 68 + 4 * quotes_field_count
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

            if quotes_field_count != 0:
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


