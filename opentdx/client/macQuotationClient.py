
from .quotationClient import QuotationClient
from .exQuotationClient import exQuotationClient
from .commonClientMixin import CommonClientMixin
from opentdx.const import mac_hosts, mac_ex_hosts


class macQuotationClient(QuotationClient, CommonClientMixin):
    def __init__(self, multithread=False, heartbeat=False, auto_retry=False, raise_exception=False):
        super().__init__(multithread, heartbeat, auto_retry, raise_exception)
        self.hosts = mac_hosts
        self._sp_mode_enabled = True


class macExQuotationClient(exQuotationClient, CommonClientMixin):
    def __init__(self, multithread=False, heartbeat=False, auto_retry=False, raise_exception=False):
        super().__init__(multithread, heartbeat, auto_retry, raise_exception)
        self.hosts = mac_ex_hosts
        self._sp_mode_enabled = True
