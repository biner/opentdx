import json
import struct

from opentdx._typing import override

import pandas as pd
from opentdx.const import  MARKET
from opentdx.parser.baseParser import BaseParser, register_parser


@register_parser(0x1218,1)
class SymbolBelongBoard(BaseParser):
    '''股票关联行情'''
    def __init__(self, symbol: str, market: MARKET):
        self.body = struct.pack("<H8s16x21s", market.value, symbol.encode("gbk"), "Stock_GLHQ".encode("ascii"))

        # pkg = bytearray.fromhex('0000 0000 0000 0000 \
        # 0000 0000 0000 0000 0000 5374 6f63 6b5f \
        # 474c 4851 0000 0000 0000 0000 0000 00   ')


    @override
    def deserialize(self, data):
        market, query_info_str, ext = struct.unpack("<H12s5x8s", data[:27])

        list_raw = struct.unpack(f"<{len(data) - 27}s", data[27:])
        python_list = json.loads(list_raw.decode("gbk"))

        df = pd.DataFrame()
        if len(python_list) > 0:
            # 2. 第二步：List 转 Pandas DataFrame（核心操作）
            # 定义列名（根据数据含义命名，更易理解）
            if  len(python_list[0]) == 9:
                columns = ["board_type", "market", "board_symbol", "board_symbol_name", "close", "pre_close", "涨停数", "跌停数", "最相似"]
            elif  len(python_list[0]) == 13:
                columns = ["board_type", "market", "board_symbol", "board_symbol_name", "close", "pre_close", 
                        "speed_pct", "symbol_market", "symbol", "symbol_name", "symbol_close", "symbol_pre_close", "symbol_speed_pct"]  # 根据实际含义命名
            else:
                raise ValueError("不支持的字段数量")

            # 转换为DataFrame
            df = pd.DataFrame(python_list, columns=columns)

            # 3. 第三步：数据类型转换（字符串转数值）
            # 把数值型列从字符串转为浮点数/整数
            numeric_columns = ["close", "pre_close" ]
            for col in numeric_columns:
                df[col] = pd.to_numeric(
                    df[col], errors="coerce"
                )  # errors='coerce' 把无法转换的转为NaN

        return df
