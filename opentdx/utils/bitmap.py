# coding=utf-8
from enum import Enum, IntEnum
from typing import Union, List
from opentdx.utils.log import log

SYMBOL_QUOTES_DEFAULT_HEX = "ffbc81cc3f080300000000000000000000000000"
BOARD_MEMBERS_QUOTES_DEFAULT_HEX = "fffce1cc3f080301000000000000000000000000"

QUOTES_DEBUG_HEX =     "ff ff ff ff ff ff ff ff 00 00 00 00 00 00 00 00 00 00 00 00"
QUOTES_DEBUG_ALL_HEX = "ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff"
# 定义字段位图映射 (根据 TDX 协议定义)
# 每一位代表一个4字节的字段是否存在
# 通过对比静态解析和动态解析验证得出（基于实测数据）
# 
# 注意：所有字段（包括基础字段）都受位图控制
# 位0-5: 基础字段 (pre_close, open, high, low, close, vol)
# 位6+: 扩展字段
#
# 格式: {位位置: (字段名, 格式字符串, "说明")}
# 格式字符串: '<f' = float (4字节浮点数), '<I' = uint32 (4字节无符号整数)
FIELD_BITMAP_MAP = {
    # 基础字段（位0x0-0x5）- ✅ 100% 确认
    0x0: ("pre_close", '<f', "昨收"),
    0x1: ("open", '<f', "开盘价"),
    0x2: ("high", '<f', "最高价"),
    0x3: ("low", '<f', "最低价"),
    0x4: ("close", '<f', "收盘价"),
    0x5: ("vol", '<I', "成交量"),
    0x6: ("vol_ratio", '<f', "量比"),
    0x7: ("amount", '<f', "总金额（单位：元，注意：港股单位不同）"),
    
    # 扩展字段（位0x8-0xF）
    0x8: ("inside_volume", '<I', "内盘"),  # ✅ 920627验证：CSV内盘=20999, bitmap=20999
    0x9: ("outside_volume", '<I', "外盘"),  # ✅ 920627验证：CSV外盘=24576, bitmap=24576 
    0xa: ("total_shares", '<f', "总股数(单位万)"),
    0xb: ("float_shares", '<f', "流通股(单位万)"), # 港股为H股数,也是流通股
    0xc: ("eps", '<f', "每股收益"), 
    0xd: ("net_assets", '<f', "净资产"),  # 
    0xe: ("unkonw_action_price", '<f', "未知价"),# （国内通常为3, 9,12） 美股港股与close相等
    0xf: ("total_market_cap_ab", '<f', "AB股总市值"),  # 港股代表H市值
    
    # 位0x10-0x17
    0x10: ("pe_dynamic", '<f', "市盈率(动)"),
    0x11: ("bid", '<f', "买价"),  
    0x12: ("ask", '<f', "卖价"), 
    0x13: ("server_update_date", '<I', "服务器更新日期 YYYYMMDD"),
    0x14: ("server_update_time", '<I', "服务器更新时间 HHMMSS"),
    0x15: ("lot_size_info", '<I', "未确定"), # 港股 格式为 240000500 ,美股味 550000001  , 24/55不确定 500和1代表lot_size
    # 0x16: ("unknown_23", '<f', "未确定"),
    0x17: ("dividend_yield", '<f', "股息"), 
    
    0x18: ("bid_volume", '<I', "买量"),
    0x19: ("ask_volume", '<I', "卖量"),
    0x1a: ("last_volume", '<I', "现量"), 
    0x1b: ("turnover", '<f', "换手"),
    0x1c: ("industry", '<I', "行业"),#行业分类代码（5位数字）- 行业板块内固定，地域/概念板块内多样
    0x1d: ("industry_change_up", '<f', "行业涨跌幅"), 
    0x1e: ("some_bitmap", '<I', "位图"),
    0x1f: ("decimal_point", '<I', "数据精度"),
    
    0x20: ("buy_price_limit", '<f', "涨停价"),  
    0x21: ("sell_price_limit", '<f', "跌停价"), 
    0x22: ("unknown_34", '<I', "（港股通常为15）"),
    0x23: ("lot_size", '<I', "每手股数(港股)"), # 国内股票为板块id, 1 => 880201 14=> 880214
    0x24: ("pre_ipov", '<f', "昨IPOV)"), #ETF-昨日IPOV
    0x25: ("speed_pct", '<f', "涨速"), 
    0x26: ("avg_price", '<f', "均价"),  
    0x27: ("ipov", '<f', "IPOV"),  #ETF-IPOV
    
    0x28: ("pe_ttm_vol_related", '<f', "市盈率TTM（与vol相关0.96，可能不是真正的PE TTM）"),  # ✅ 高相关
    0x29: ("ex_price_placeholder", '<f', "收盘价占位（与amount相关0.89，需验证）"),  # ⚠️ 中等相关
    0x2a: ("unknown_36_amount_related", '<f', "未知字段36（与amount相关0.90，需验证）"),  # ⚠️ 中等相关
    0x2b: ("flag_kcb", '<I', "科创板标志 "), #688开头30101 #300开头50101
    0x2c: ("flag_bj", '<I', "北交所标志"),
    0x2d: ("unknown_field_39_vol_related", '<f', "未知字段39（与vol相关0.99，高度相关）"),  # ✅ 高相关

    
    0x30: ("pe_ttm", '<f', "市盈率TTM"),
    0x31: ("pe_static", '<f', "市盈率静"),
    
    0x38: ("unknown_close_price", '<f', "美股字段"), 

    
    0x3b: ("change_20d_pct", '<f', "20日涨幅%"),  # ✅ 920627验证：CSV=-12.55, bitmap=-12.55
    0x3c: ("ytd_pct", '<f', "年初至今%"),  # ✅ 920627验证：CSV=-3.8, bitmap=-3.8

    
    0x40: ("mtd_pct", '<f', "月初至今%"),  # ✅ 920627验证：CSV=6.11, bitmap=6.11
    0x41: ("change_1y_pct", '<f', "一年涨幅%"),  # ✅ 920627验证：CSV=-17.29, bitmap=-17.29
    0x42: ("prev_change_pct", '<f', "昨涨幅%"),  # ✅ 920627验证：CSV=-1.14, bitmap=-1.14
    0x43: ("change_3d_pct", '<f', "3日涨幅%"),  # ✅ 920627验证：CSV=12.1, bitmap=12.10 (注：CSV振幅%=12.19是不同的字段)
    0x44: ("change_60d_pct", '<f', "60日涨幅%"),  # ✅ 920627验证：CSV=-15.37, bitmap=-15.37
    0x45: ("change_5d_pct", '<f', "5日涨幅%"),  # ✅ 920627验证：CSV=6.44, bitmap=6.44
    0x46: ("change_10d_pct", '<f', "10日涨幅%"),  # ✅ 920627验证：CSV=1.64, bitmap=1.64
    
    0x48: ("low_copy", '<f', "最低价(备份)"),  
    0x49: ("low_copy2", '<f', "最低价(备份)"), 
    0x4a: ("ah_code", '<I', "对应A/H股code,不足位数前面补0"), # 600876 对应 1108 /  06881 对应 601881
    0x4b: ("unknown_code", '<I', "少部分有数据,6位数字 123247"),

    
    # 新发现的扩展字段（位0x50-0x57）- 通过 000100 数据发现

    0x57: ("open_amount", '<f', "开盘金额（元）"),  # ✅ 000100验证：CSV=1322.18万, bitmap=13221810元

    0x59: ("activity", '<I', "活跃度"), 
    0x5c: ("consecutive_up_days", '<i', "连涨天"), # 正数代表连涨，负数代表连跌 
    
    0x6a: ("amount_2m", '<f', "2分钟金额"), 
}

class FieldBit(IntEnum):
    PRE_CLOSE = 0x0
    OPEN = 0x1
    HIGH = 0x2
    LOW = 0x3
    CLOSE = 0x4
    VOL = 0x5
    VOL_RATIO = 0x6
    AMOUNT = 0x7
    INSIDE_VOLUME = 0x8
    OUTSIDE_VOLUME = 0x9
    TOTAL_SHARES = 0xa
    FLOAT_SHARES = 0xb
    EPS = 0xc
    NET_ASSETS = 0xd
    UNKONW_ACTION_PRICE = 0xe
    TOTAL_MARKET_CAP_AB = 0xf
    PE_DYNAMIC = 0x10
    BID = 0x11
    ASK = 0x12
    SERVER_UPDATE_DATE = 0x13
    SERVER_UPDATE_TIME = 0x14
    LOT_SIZE_INFO = 0x15
    UNKNOWN_22 = 0x16
    DIVIDEND_YIELD = 0x17
    BID_VOLUME = 0x18
    ASK_VOLUME = 0x19
    LAST_VOLUME = 0x1a
    TURNOVER = 0x1b
    INDUSTRY = 0x1c
    INDUSTRY_CHANGE_UP = 0x1d
    SOME_BITMAP = 0x1e
    DECIMAL_POINT = 0x1f
    BUY_PRICE_LIMIT = 0x20
    SELL_PRICE_LIMIT = 0x21
    UNKNOWN_34 = 0x22
    LOT_SIZE = 0x23
    PRE_IPOV = 0x24
    SPEED_PCT = 0x25
    AVG_PRICE = 0x26
    IPOV = 0x27
    PE_TTM_VOL_RELATED = 0x28
    EX_PRICE_PLACEHOLDER = 0x29
    UNKNOWN_36_AMOUNT_RELATED = 0x2a
    FLAG_KCB = 0x2b
    FLAG_BJ = 0x2c
    UNKNOWN_FIELD_39_VOL_RELATED = 0x2d
    PE_TTM = 0x30
    PE_STATIC = 0x31
    UNKNOWN_CLOSE_PRICE = 0x38
    CHANGE_20D_PCT = 0x3b
    YTD_PCT = 0x3c
    MTD_PCT = 0x40
    CHANGE_1Y_PCT = 0x41
    PREV_CHANGE_PCT = 0x42
    CHANGE_3D_PCT = 0x43
    CHANGE_60D_PCT = 0x44
    CHANGE_5D_PCT = 0x45
    CHANGE_10D_PCT = 0x46
    LOW_COPY = 0x48
    LOW_COPY2 = 0x49
    AH_CODE = 0x4a
    UNKNOWN_CODE = 0x4b
    OPEN_AMOUNT = 0x57
    ACTIVITY = 0x59
    CONSECUTIVE_UP_DAYS = 0x5c
    AMOUNT_2M = 0x6a
    
    @property
    def info(self):
        return FIELD_BITMAP_MAP.get(self.value, {})
    
    @property
    def field_name(self):
        """返回显示名称"""
        return self.info[0] if self.info else "unknow"

# 预定义字段集合（快捷方式）
class PresetField(Enum):
    NONE = ()
    BASIC = (FieldBit.PRE_CLOSE, FieldBit.OPEN, FieldBit.HIGH, FieldBit.LOW, FieldBit.CLOSE, FieldBit.VOL)
    QUOTE = (FieldBit.BID, FieldBit.ASK, FieldBit.BID_VOLUME, FieldBit.ASK_VOLUME, FieldBit.LAST_VOLUME)
    VOLUME = (FieldBit.VOL, FieldBit.AMOUNT, FieldBit.TURNOVER, FieldBit.VOL_RATIO)
    FUNDAMENTAL = (FieldBit.TOTAL_SHARES, FieldBit.FLOAT_SHARES, FieldBit.EPS, FieldBit.NET_ASSETS)
    VALUATION = (FieldBit.PE_TTM, FieldBit.PE_STATIC, FieldBit.TOTAL_MARKET_CAP_AB)
    CHANGE = (FieldBit.CHANGE_5D_PCT, FieldBit.CHANGE_10D_PCT, FieldBit.CHANGE_20D_PCT, FieldBit.CHANGE_60D_PCT,
                FieldBit.YTD_PCT, FieldBit.MTD_PCT, FieldBit.PREV_CHANGE_PCT)
    LIMIT = (FieldBit.BUY_PRICE_LIMIT, FieldBit.SELL_PRICE_LIMIT)

    ENHANCED = (FieldBit.OPEN, FieldBit.HIGH, FieldBit.LOW, FieldBit.CLOSE, FieldBit.VOL, FieldBit.FLOAT_SHARES, FieldBit.ACTIVITY)
    AH_CODE = (FieldBit.OPEN, FieldBit.HIGH, FieldBit.LOW, FieldBit.CLOSE, FieldBit.VOL, FieldBit.AH_CODE, FieldBit.LOT_SIZE, FieldBit.INDUSTRY)

    #"fffce1cc3f080301000000000000000000000000"
    COMMON = (FieldBit.PRE_CLOSE, FieldBit.OPEN, FieldBit.HIGH, FieldBit.LOW, FieldBit.CLOSE, FieldBit.VOL,
                FieldBit.VOL_RATIO, FieldBit.AMOUNT, FieldBit.TOTAL_SHARES, FieldBit.FLOAT_SHARES, FieldBit.EPS,
                FieldBit.NET_ASSETS, FieldBit.UNKONW_ACTION_PRICE, FieldBit.TOTAL_MARKET_CAP_AB, FieldBit.PE_DYNAMIC,
                FieldBit.LOT_SIZE_INFO, FieldBit.UNKNOWN_22, FieldBit.DIVIDEND_YIELD, FieldBit.LAST_VOLUME,
                FieldBit.TURNOVER, FieldBit.SOME_BITMAP, FieldBit.DECIMAL_POINT, FieldBit.BUY_PRICE_LIMIT,
                FieldBit.SELL_PRICE_LIMIT, FieldBit.UNKNOWN_34, FieldBit.LOT_SIZE, FieldBit.PRE_IPOV,
                FieldBit.SPEED_PCT, FieldBit.FLAG_KCB, FieldBit.PE_TTM, FieldBit.PE_STATIC, FieldBit.UNKNOWN_CLOSE_PRICE)
    ALL = tuple(FieldBit)


# def fields_to_filter(field_names: Union[str, List[str]]) -> int:
#     """
#     将字段名列表（或预定义集合名）转换为 filter 整数位掩码
    
#     Args:
#         field_names: 可以是字段名列表，或预定义集合的键（如 'basic'），
#                      或使用 '+' 连接的组合字符串，如 'basic+quote'
    
#     Returns:
#         整数位掩码，每一位代表一个字段位位置
#     """
#     if isinstance(field_names, str):
#         if '+' in field_names:
#             parts = field_names.split('+')
#             names = []
#             for part in parts:
#                 if part in PRESET_FIELDS:
#                     names.extend(PRESET_FIELDS[part])
#                 else:
#                     names.append(part)
#         elif field_names in PRESET_FIELDS:
#             names = PRESET_FIELDS[field_names]
#         else:
#             names = [field_names]
#     else:
#         names = field_names
    
#     filter_val = 0
#     for name in names:
#         if name in FIELD_NAME_TO_BIT:
#             bit_pos = FIELD_NAME_TO_BIT[name]
#             filter_val |= (1 << bit_pos)
#         else:
#             log.warning(f"未知字段名: {name}，已忽略")
#     return filter_val


def get_active_fields_from_bitmap(bitmap_bytes: bytes) -> list[int]:
    bitmap_int = int.from_bytes(bitmap_bytes, 'little')
    active_bits = []
    while bitmap_int:
        lowbit = bitmap_int & -bitmap_int          # 取最低位的1
        bit_pos = lowbit.bit_length() - 1          # 计算位置
        active_bits.append(bit_pos)
        bitmap_int ^= lowbit                       # 清除该位
    return active_bits


def convert_fields_to_filter(fields: List[FieldBit] | PresetField | None) -> int:
    """
    将 fields 参数（FieldBit 列表或 PresetField 枚举）转换为 filter 整数位掩码
    
    Args:
        fields: 可以是以下类型之一：
                - None: 返回 0
                - list[FieldBit]: FieldBit 枚举列表，如 [FieldBit.PRE_CLOSE, FieldBit.OPEN]
                - PresetField: 预定义字段集合枚举，如 PresetField.BASIC
    
    Returns:
        整数位掩码，如果 fields 为 None 则返回 0
    
    Examples:
        >>> # 使用 PresetField
        >>> convert_fields_to_filter(PresetField.BASIC)
        
        >>> # 使用 FieldBit 列表
        >>> convert_fields_to_filter([FieldBit.PRE_CLOSE, FieldBit.OPEN, FieldBit.HIGH])
        
        >>> # 使用 None
        >>> convert_fields_to_filter(None)  # 返回 0
    """
    if fields is None:
        return 0
    
    # 处理 PresetField 枚举
    if isinstance(fields, PresetField):
        field_bits = fields.value
    else:
        # 假设是 FieldBit 列表
        field_bits = fields
    
    filter_val = 0
    for bit in field_bits:
        if isinstance(bit, FieldBit):
            filter_val |= (1 << bit.value)
        else:
            log.warning(f"无效的字段位: {bit}，已忽略")
    
    return filter_val
