from datetime import date

import pandas as pd
from tdx_mcp.client import QuotationClient, exQuotationClient
from tdx_mcp.const import ADJUST, BLOCK_FILE_TYPE, CATEGORY, EX_CATEGORY, FILTER_TYPE, MARKET, PERIOD, EX_BOARD_TYPE, BOARD_TYPE
from tdx_mcp.const import mixin_hosts, ex_mixin_hosts
from tdx_mcp.parser.ex_quotation import file, goods
from tdx_mcp.parser.quotation import server, stock


if __name__ == "__main__":
    client = QuotationClient()
    client.hosts = mixin_hosts
    client.connect().login()

        
    exClient = exQuotationClient()
    exClient.hosts = ex_mixin_hosts
    exClient.connect().login()

    df = (pd.DataFrame(exClient.get_list()))
    
    print(df[30:60],len(df))

    show_df = df[df['code'].str.startswith('88')]

    print(show_df[40:80])
    
    client.disconnect()
    exClient.disconnect()


