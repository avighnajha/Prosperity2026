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
            cur_time_trades = self.trades_df[self.trades_df['timestamp'] == t] if not self.trades_df.empty else pd.DataFrame()

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

            #Matches orders (aggressive first, then passive)
            fills = self.match_engine(cur_time_prices, orders, cur_time_trades, t)
            
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
    
    def _fill_order_across_levels(self, product, product_prices, remaining_quantity, price_prefix):
        """
        Fill an order across multiple price levels.
        
        Args:
            product: Product name for Trade creation
            product_prices: Series of prices for this product
            remaining_quantity: Amount still to fill
            price_prefix: 'bid' for sell orders, 'ask' for buy orders
        
        Returns:
            Tuple of (list of Trade objects, remaining_quantity after fills)
        """
        trades = []
        level = 1
        
        while remaining_quantity > 0:
            price_col = f'{price_prefix}_price{level}'
            volume_col = f'{price_prefix}_volume{level}'
            
            if price_col not in product_prices.index or pd.isna(product_prices[price_col]):
                break
            
            price = product_prices[price_col]
            available_volume = int(product_prices[volume_col])
            
            fill_quantity = min(remaining_quantity, available_volume)
            trades.append(Trade(product, price, fill_quantity))
            remaining_quantity -= fill_quantity
            
            level += 1
        
        return trades, remaining_quantity
    
    def _fill_passive_from_trades(self, product, order, remaining_quantity, trades_df):
        """
        Passively fill an order by matching against market trades at the same timestamp.
        
        Args:
            product: Product name
            order: Order object with price attribute
            remaining_quantity: Amount still to fill after aggressive matching
            trades_df: DataFrame of market trades at this timestamp
        
        Returns:
            List of Trade objects representing passive fills
        """
        passive_trades = []
        
        if trades_df.empty or remaining_quantity == 0:
            return passive_trades
        
        # Filter trades for this product
        product_trades = trades_df[trades_df['product'] == product]
        
        if product_trades.empty:
            return passive_trades
        
        # Get unique prices and iterate through them
        for _, trade_row in product_trades.iterrows():
            if remaining_quantity <= 0:
                break
            
            market_price = trade_row['price']
            market_volume = trade_row['quantity']
            
            # Check if this trade matches our price condition
            if order.quantity < 0:  # Sell order
                # Passive sell fill: market_trade_price >= my_limit_price
                if market_price >= order.price:
                    fill_quantity = min(remaining_quantity, market_volume)
                    # Use conservative price (my limit price)
                    passive_trades.append(Trade(product, order.price, fill_quantity))
                    remaining_quantity -= fill_quantity
            else:  # Buy order
                # Passive buy fill: market_trade_price <= my_limit_price
                if market_price <= order.price:
                    fill_quantity = min(remaining_quantity, market_volume)
                    # Use conservative price (my limit price)
                    passive_trades.append(Trade(product, order.price, fill_quantity))
                    remaining_quantity -= fill_quantity
        
        return passive_trades
    
    def match_engine(self, prices, orders, trades_df=None, timestamp=None):
        """
        Matches orders from the trader against the current market prices.
        First attempts aggressive matching against OrderDepth, then passive matching against trades.

        Args:
            prices: DataFrame containing the current market prices (OrderDepth)
            orders: Dictionary of orders from the trader
            trades_df: DataFrame of market trades at this timestamp (for passive fills)
            timestamp: Current timestamp (for context)

        Returns:
            Dictionary of fills representing the matched trades
        """
        fills = {}

        # Aggressive matching against OrderDepth
        for product, order_list in orders.items():
            for order in order_list:
                remaining_quantity = abs(order.quantity)
                product_prices = prices[prices['product'] == product].iloc[0]
                
                # Aggressive matching
                if order.quantity < 0:  # Sell order - match against bids
                    aggressive_trades, remaining_quantity = self._fill_order_across_levels(
                        product, product_prices, remaining_quantity, 'bid'
                    )
                else:  # Buy order - match against asks
                    aggressive_trades, remaining_quantity = self._fill_order_across_levels(
                        product, product_prices, remaining_quantity, 'ask'
                    )
                
                fills.setdefault(product, []).extend(aggressive_trades)
                
                # Passive matching against trades
                if remaining_quantity > 0 and trades_df is not None and not trades_df.empty:
                    passive_trades = self._fill_passive_from_trades(product, order, remaining_quantity, trades_df)
                    fills.setdefault(product, []).extend(passive_trades)

        return fills


backtester = Backtester(Trader, prices_df, pd.DataFrame())

price_groups = prices_df.groupby('timestamp')
cur_time_prices = price_groups.get_group(0)


order_depths = backtester.get_order_depths(cur_time_prices)
print(order_depths["TOMATOES"].buy_orders, order_depths["EMERALDS"].buy_orders)
print(order_depths["TOMATOES"].sell_orders, order_depths["EMERALDS"].sell_orders)







    
    