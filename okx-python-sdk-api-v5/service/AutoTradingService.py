import time
import traceback

import okx.Market_api as Market
import okx.Trade_api as Trade
import okx.Account_api as Account
from datetime import datetime, timedelta
from APIKEY import *


class AutoTradingService(object):
    def __init__(self, apikey, secretkey, passphrase, symbol="BTC-USDT-SWAP", error_margin=100, trade_size=100,
                 max_positions=300, flag="1"):
        self.apikey = apikey
        self.secretkey = secretkey
        self.passphrase = passphrase
        self.symbol = symbol
        self.error_margin = error_margin
        self.trade_size = trade_size
        self.max_positions = max_positions
        self.flag = flag

        self.marketAPI = Market.MarketAPI(apikey, secretkey, passphrase, False, flag)
        self.tradeAPI = Trade.TradeAPI(apikey, secretkey, passphrase, False, flag)
        self.accountAPI = Account.AccountAPI(apikey, secretkey, passphrase, False, flag)

        self.last_bullish_candle = None
        self.last_bearish_candle = None
        self.long_orders = []
        self.short_orders = []

        self.initialize()

    def initialize(self):
        # 设置杠杆
        # self.accountAPI.set_leverage(instId=self.symbol, lever='10', mgnMode='isolated', posSide='long')

        # 获取当前订单
        positions = self.get_positions()
        print(f"Current positions: {positions}")
        if positions:
            for pos in positions['data']:
                if pos['instId'] == self.symbol:
                    if pos['posSide'] == 'long':
                        self.long_orders.append(pos['posId'])
                    elif pos['posSide'] == 'short':
                        self.short_orders.append(pos['posId'])
        print(f"Long orders: {self.long_orders}")
        print(f"Short orders: {self.short_orders}")
        # 获取最近的一个4小时阳线和阴线
        candles = self.get_candles(self.symbol, "4H")
        # print(f"Candles: {candles}")
        for candle in candles[::]:
            if candle[8] == '1':
                open_price = float(candle[1])
                close_price = float(candle[4])
                if abs(open_price - close_price) > self.error_margin:
                    if close_price > open_price and not self.last_bullish_candle:
                        self.last_bullish_candle = candle
                    elif close_price < open_price and not self.last_bearish_candle:
                        self.last_bearish_candle = candle
                    if self.last_bullish_candle and self.last_bearish_candle:
                        break
        print(f"Last bullish candle: {self.last_bullish_candle}")
        print(f"Last bearish candle: {self.last_bearish_candle}")

    def get_candles(self, symbol, timeframe):
        return self.marketAPI.get_candlesticks(instId=symbol, bar=timeframe)['data']

    def place_order(self, instId, side, size, price, stop_price):
        return self.tradeAPI.place_order(
            instId=instId,
            tdMode="isolated",
            side=side,
            ordType="limit",
            px=str(price),
            sz=str(size),
            stopPx=str(stop_price),
            reduceOnly=False
        )

    def place_algo_order(self, instId, side, posSide, size, price, stop_price):
        return self.tradeAPI.place_algo_order(
            instId=instId,
            tdMode="isolated",
            side=side,
            posSide=posSide,
            ordType="trigger",
            triggerPx=str(price),
            orderPx=str(-1),
            sz=str(size),
            slTriggerPx=str(stop_price),
            slOrdPx=str(-1),
            reduceOnly=False
        )

    def modify_stop_order(self, instId, side, posSide, size, stop_price):
        return self.tradeAPI.place_algo_order(
            instId=instId,
            tdMode="isolated",
            side=side,
            posSide=posSide,
            ordType="conditional",
            orderPx=str(-1),
            slTriggerPx=str(stop_price),
            slOrdPx=str(-1),
            cxlOnClosePos=True,
            sz=str(size),
            reduceOnly=True
        )

    def place_stop_order(self, instId, side, size, stop_price):
        print(f"Placing {side} stop order for {size} contracts at {stop_price} price")
        return self.tradeAPI.place_order(
            instId=instId,
            tdMode="isolated",
            side=side,
            ordType="stop-market",
            stopPx=str(stop_price),
            sz=str(size)
        )

    def get_positions(self):
        return self.accountAPI.get_positions(instType="SWAP")

    def get_order_algos_list(self):
        return self.tradeAPI.order_algos_list(instType="SWAP", ordType="trigger")

    def cancel_algo_order(self, algoId):
        params = [{"instId": self.symbol, "algoId": algoId}]
        print(f"Cancelling algo order {algoId}")
        # print(params)
        return self.tradeAPI.cancel_algo_order(params)

    def cancel_order(self, order_id):
        return self.tradeAPI.cancel_order(instId=self.symbol, ordId=order_id)

    def modify_order(self, order_id, new_stop_price):
        return self.tradeAPI.amend_order(
            instId=self.symbol,
            ordId=order_id,
            newSlTriggerPx=str(new_stop_price),
            newSlOrdPx=str(-1)
        )

    def run_strategy(self):
        try:
            candles = self.get_candles(self.symbol, "4H")
            latest_candle = candles[1]
            open_price = float(latest_candle[1])
            close_price = float(latest_candle[4])
            high_price = float(latest_candle[2])
            low_price = float(latest_candle[3])
            candles_ts = latest_candle[0]

            if abs(open_price - close_price) > self.error_margin:
                if close_price > open_price:
                    self.last_bullish_candle = latest_candle
                else:
                    self.last_bearish_candle = latest_candle

            positions = self.get_positions()['data']
            total_long_size = sum([float(pos['availPos']) for pos in positions if pos['posSide'] == 'long'])
            total_short_size = sum([float(pos['availPos']) for pos in positions if pos['posSide'] == 'short'])

            print(f"Total long size: {total_long_size}")
            print(f"Total short size: {total_short_size}")

            # 修改已成交订单的止损价
            for pos in positions:
                if pos['posSide'] == 'long':
                    stop_price = float(self.last_bearish_candle[3]) - self.error_margin
                    order = self.modify_stop_order(self.symbol, "sell", "long", total_long_size, stop_price)
                    print(order)
                elif pos['posSide'] == 'short':
                    stop_price = float(self.last_bullish_candle[2]) + self.error_margin
                    order = self.modify_stop_order(self.symbol, "buy", "short", total_short_size, stop_price)
                    print(order)
            # 获取未完成策略委托单列表
            order_algos_list = self.get_order_algos_list()['data']
            if order_algos_list:
                for pos in order_algos_list:
                    self.cancel_algo_order(pos['algoId'])
                # self.short_orders.clear()
                # self.long_orders.clear()

            # 开多头单
            if self.last_bullish_candle and float(self.last_bullish_candle[2]) + self.error_margin:
                if total_long_size + self.trade_size <= self.max_positions:
                    stop_price = float(self.last_bearish_candle[3]) - self.error_margin
                    order = self.place_algo_order(self.symbol, "buy", "long", self.trade_size,
                                                  float(self.last_bullish_candle[2])
                                                  + self.error_margin, stop_price)
                    print(order)
                    # self.long_orders.append(order['data'][0]['ordId'])

            # 开空头单
            if self.last_bearish_candle and float(self.last_bearish_candle[3]) - self.error_margin:
                if total_short_size + self.trade_size <= self.max_positions:
                    stop_price = float(self.last_bullish_candle[2]) + self.error_margin
                    order = self.place_algo_order(self.symbol, "sell", "short", self.trade_size,
                                                  float(self.last_bearish_candle[3])
                                                  - self.error_margin, stop_price)
                    print(order)
                    # self.short_orders.append(order['data'][0]['ordId'])
        except Exception as e:
            traceback.print_exc()
            print(f"Error: {e}")

    def next_run_time(self):
        now = datetime.utcnow()
        hour = now.hour - now.hour % 4 + 4
        next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if next_time <= now:
            next_time += timedelta(hours=4)
        return next_time

    def start_trading(self):
        while True:
            next_time = self.next_run_time()
            sleep_time = (next_time - datetime.utcnow()).total_seconds()
            print(f"Next run time: {next_time}, sleep time: {sleep_time} seconds")
            time.sleep(sleep_time)
            # time.sleep(20)
            while True:
                candles = self.get_candles(self.symbol, "4H")
                latest_candle_time = int(candles[0][0]) / 1000
                print(f"Latest candle time: {datetime.utcfromtimestamp(latest_candle_time)}")
                if datetime.utcfromtimestamp(latest_candle_time) >= next_time:
                    print(f"Latest candle time: {datetime.utcfromtimestamp(latest_candle_time)}")
                    print(f"Next run time: {next_time}")
                    self.run_strategy()
                    break
                time.sleep(1)


# 使用示例
if __name__ == "__main__":
    apikey = api_key
    secretkey = secret_key
    passphrase = passphrase
    trading_service = AutoTradingService(apikey, secretkey, passphrase)
    # for test
    trading_service.run_strategy()
    trading_service.start_trading()
