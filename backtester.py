#Point at a specific trader
import pandas as pd

from tutorial import *
from engine.datamodel import *
from pandas import DataFrame as df

from tutorial.tutorial import Trader

prices_df = pd.read_csv('tutorial/data/prices_round_0_day_-1.csv', delimiter=';')

class Backtester:
    def __init__(self, Trader, prices_df : df, trades_df : df):
        self.trader = Trader()
        self.prices_df = prices_df
        self.trades_df = trades_df

        self.current_position = {"PEARLS": 0, "BANANAS": 0} 
        self.current_cash = 0
        self.last_trader_data = ""
        self.own_trades = {"PEARLS": [], "BANANAS": []}

    
    def run(self):
        price_groups = self.prices_df.groupby('timestamp')
        timestamps = sorted(price_groups.groups.keys())

        for t in timestamps:
            cur_time_prices = price_groups.get_group(t)

            #Current trading state including current positions
            orders = self.get_order_depths(cur_time_prices)

            state = TradingState(
                traderData=self.last_trader_data,
                timestamp=t,
                listings={},
                order_depths=orders,
                own_trades=self.own_trades,
                market_trades={},
                position=self.current_position,
                observations={})

            #Run trader
            orders, conv, trader_data = self.trader.run(state)

            #Matches orders and updates ledger
            fills = self.match_engine(t, orders)
            
            # Update ledger
            self.update_ledger(fills)
            self.last_trader_data = trader_data
            self.own_trades = fills # These become 'own_trades' in the next tick
    
    def get_order_depths(self, prices):
        # price : volume

        order_depths = {}

        for idx, row in prices.iterrows():
            bids = {}
            asks = {}

            asset = row["product"]
            orders = OrderDepth()

            for col in prices.columns:
                if pd.isna(row[col]) or row[col] == 0:
                    continue
                if col.startswith("bid_price"):
                    vol_col = col.replace("price", "volume")

                    #price : volume
                    self.add_volume(bids, int(row[col]), int(row[vol_col]))

                elif col.startswith("ask_price"):
                    vol_col = col.replace("price", "volume")
                    
                    #price : volume
                    self.add_volume(asks, int(row[col]), -1*int(row[vol_col]))   
            orders.buy_orders, orders.sell_orders = bids, asks
            order_depths[asset] = orders
        return order_depths
    
    def add_volume(self, order_dict, price, volume):
        if price in order_dict:
            order_dict[price] += volume
        else:
            order_dict[price] = volume

backtester = Backtester(Trader, prices_df, pd.DataFrame())

price_groups = prices_df.groupby('timestamp')
cur_time_prices = price_groups.get_group(0)


order_depths = backtester.get_order_depths(cur_time_prices)
print(order_depths["TOMATOES"].buy_orders, order_depths["EMERALDS"].buy_orders)
print(order_depths["TOMATOES"].sell_orders, order_depths["EMERALDS"].sell_orders)







    
    