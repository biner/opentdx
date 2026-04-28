import json
import struct
from opentdx._typing import override

import pandas as pd
from opentdx.const import MARKET
from opentdx.parser.baseParser import BaseParser, register_parser


@register_parser(0x1218, 2)
class SymbolZJLX(BaseParser):

    """
    资金流向解析器
    解析 Stock_ZJLX 查询返回的资金流向数据
    包含主力流入流出、散户流入流出等信息
    """
    
    def __init__(self, symbol: str, market: MARKET):
        self.body = struct.pack("<H8s16x21s", market.value, symbol.encode("gbk"), "Stock_ZJLX".encode("ascii"))

    @override
    def deserialize(self, data):
        market, query_info_str, ext = struct.unpack("<H12s5x8s", data[:27])
        
        list_raw = struct.unpack(f"<{len(data) - 27}s", data[27:])
        python_list = json.loads(list_raw.decode("gbk"))
        
        df = pd.DataFrame()
        if len(python_list) > 0 and len(python_list) >= 2:

            # python_list[0]: 今日资金流向（4个字段）
            # python_list[1]: 5日资金流向（6个字段）
            today_data = python_list[0]    # ["主力流入", "主力流出", "散户流入", "散户流出"]
            five_days_data = python_list[1]  # 根据实际数据修正顺序
            
            # 定义列名（根据截图和实际数据对比修正）
            columns = [
                # 今日资金流向
                "今日主力流入",
                "今日主力流出",
                "今日散户流入",
                "今日散户流出",
                # 5日资金流向（修正后的顺序）
                "5日主买",          # 索引0: 276,671.8万
                "5日主卖",          # 索引1: 348,667万
                "5日超大单净额",    # 索引2: -17,784.2万
                "5日大单净额",      # 索引3: -6,786.7万
                "5日中单净额",      # 索引4: 8,398.3万
                "5日小单净额",      # 索引5: 16,172.5万
            ]
            
            # 合并今日和5日数据
            merged_data = today_data + five_days_data
            
            # 创建DataFrame
            df = pd.DataFrame([merged_data], columns=columns)
            
            # 数据类型转换：将所有列从字符串转为浮点数
            for col in columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # 计算一些衍生指标
            if "今日主力流入" in df.columns and "今日主力流出" in df.columns:
                df["今日主力净流入"] = df["今日主力流入"] - df["今日主力流出"]
            
            if "今日散户流入" in df.columns and "今日散户流出" in df.columns:
                df["今日散户净流入"] = df["今日散户流入"] - df["今日散户流出"]
            
            if "5日主买" in df.columns and "5日主卖" in df.columns:
                df["5日主力净流入"] = df["5日主买"] - df["5日主卖"]
        
        return df
