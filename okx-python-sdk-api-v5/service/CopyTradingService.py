import datetime

from okx import Copytrading_api as CopyTrading
from okx import Account_api as Account
from APIKEY import *
import json
import time


class CopyTradingService(object):
    def __init__(self):
        # flag是实盘与模拟盘的切换参数 flag is the key parameter which can help you to change between demo and real trading.
        # flag = '1'  # 模拟盘 demo trading
        flag = '0'  # 实盘 real trading

        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, use_server_time=False, flag=flag)
        self.copyTradingAPI = CopyTrading.CopytradingAPI(api_key, secret_key, passphrase, False, flag)

    def runa(self):
        try:
            # account api
            # 查看账户持仓风险 GET Position_risk
            # result = accountAPI.get_position_risk('SWAP')
            # 查看账户余额  Get Balance
            result = self.accountAPI.get_account()
            print(json.dumps(result))
            # copy trading api
            # 540D011FDACCB47A 百万 127BE725D7F66EED
            # D5E7A8430A35CA84 墙头草
            # result = copyTradingAPI.first_copy_settings(name='540D011FDACCB47A', copymode='SMART_COPY', amount='100')
            # 59206 没有位置
            # result = self.copyTradingAPI.get_existing_leading_positions()
            # result = self.copyTradingAPI.get_existing_positions('540D011FDACCB47A')
            # print(json.dumps(result))
            while True:
                # result = self.copyTradingAPI.first_copy_settings(uniqueCode='540D011FDACCB47A', copyTotalAmt='100',
                #                                                  copyAmt='100', copyInstIdType='copy',
                #                                                  copyMgnMode='isolated', subPosCloseType='copy_close',
                #                                                  instType='SWAP')
                # result = self.copyTradingAPI.current_subpositions(uniqueCode='D5E7A8430A35CA84')
                result = self.copyTradingAPI.get_existing_positions(unique='D5E7A8430A35CA84')
                print(json.dumps(result))
                # print(result.get("code"))

                if result.get("code") == '0' or result.get("code") == '59279':
                    print("Code is 1. Ending loop.")
                    break
                else:
                    print("Code is not 1. Sleeping for 1 second.")
                    print(datetime.datetime.now())
                    time.sleep(0.5)
        except Exception as e:
            print("遇到异常：", str(e))
            time.sleep(60)
            self.runa()


if __name__ == '__main__':
    service = CopyTradingService()
    service.runa()
