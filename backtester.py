#Point at a specific trader
from tutorial import *
from engine.datamodel import *

class Backtester:
    def __init__(self, Trader, prices_df, trades_df):
        self.trader = Trader()
        self.prices_df = prices_df
        self.trades_df = trades_df

        self.current_position = {"PEARLS": 0, "BANANAS": 0} 
        self.current_cash = 0
        self.last_trader_data = ""
        self.own_trades = {"PEARLS": [], "BANANAS": []}

    
    def run(self):
        # csv to list of TradingStates by timesplit
        timestamps = []

        for t in timestamps:
            #Current trading state including current positions
            state = self.getState(t)


            orders, conv, trader_data = self.trader.run(state)

            #Matches orders and updates ledger
            fills = self.match_engine(t, orders)
            
            # Update ledger
            self.update_ledger(fills)
            self.last_trader_data = trader_data
            self.own_trades = fills # These become 'own_trades' in the next tick







    
    