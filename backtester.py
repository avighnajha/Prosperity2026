import pandas as pd
from engine.datamodel import *
from pandas import DataFrame as df
from tutorial.tutorial import Trader

prices_df = pd.read_csv('tutorial/data/prices_round_0_day_-1.csv', delimiter=';')

class Backtester:
    def __init__(self, Trader, prices_df: df, trades_df: df):
        if isinstance(Trader, type):
            self.trader = Trader()
        else:
            self.trader = Trader
        self.prices_df = prices_df
        self.trades_df = trades_df

        # Get all products from dfs
        self.products = self.prices_df['product'].unique()
        self.current_position = {product: 0 for product in self.products}
        self.own_trades = {product: [] for product in self.products}

        self.current_cash = 0
        self.last_trader_data = ""

    def run(self):
        price_groups = self.prices_df.groupby('timestamp')
        timestamps = sorted(price_groups.groups.keys())

        for t in timestamps:
            cur_time_prices = price_groups.get_group(t)
            cur_time_trades = self.trades_df[self.trades_df['timestamp'] == t] if not self.trades_df.empty else pd.DataFrame()

            # Reset own trades so the state only contains trades from the PREVIOUS tick
            state_own_trades = self.own_trades.copy()
            self.own_trades = {product: [] for product in self.current_position.keys()} 

            order_depths = self.get_order_depths(cur_time_prices)

            state = TradingState(
                traderData=self.last_trader_data,
                timestamp=t,
                listings={},
                order_depths=order_depths,
                own_trades=state_own_trades,
                market_trades={},
                position=self.current_position,
                observations={})

            # Run trader
            orders, conv, trader_data = self.trader.run(state)

            # Matches orders
            fills = self.match_engine(cur_time_prices, orders, cur_time_trades, t)
            
            # Update ledger
            self.update_ledger(fills)
            self.last_trader_data = trader_data

    def get_order_depths(self, prices):
        order_depths = {}
        for idx, row in prices.iterrows():
            bids, asks = {}, {}
            asset = row["product"]
            orders = OrderDepth()

            for col in prices.columns:
                if pd.isna(row[col]) or row[col] == 0:
                    continue
                if col.startswith("bid_price"):
                    vol_col = col.replace("price", "volume")
                    # Check that volume is not 0 or NaN before adding
                    if pd.isna(row[vol_col]) or row[vol_col] == 0:
                        continue
                    self.add_volume(bids, int(row[col]), int(row[vol_col]))
                elif col.startswith("ask_price"):
                    vol_col = col.replace("price", "volume")
                    # Check that volume is not 0 or NaN before adding
                    if pd.isna(row[vol_col]) or row[vol_col] == 0:
                        continue
                    self.add_volume(asks, int(row[col]), -1*int(row[vol_col]))   
            
            orders.buy_orders, orders.sell_orders = bids, asks
            order_depths[asset] = orders
        return order_depths

    def add_volume(self, order_dict, price, volume):
        if price in order_dict:
            order_dict[price] += volume
        else:
            order_dict[price] = volume

    def _fill_order_across_levels(self, product, product_prices, remaining_quantity, price_prefix, order_price, is_sell, t):
        trades = []
        level = 1
        
        while remaining_quantity > 0:
            price_col = f'{price_prefix}_price_{level}'
            volume_col = f'{price_prefix}_volume_{level}'
            
            if price_col not in product_prices.index or pd.isna(product_prices[price_col]):
                break

            mkt_price = int(product_prices[price_col])
            mkt_volume = abs(int(product_prices[volume_col]))
            
            # Price Guard: Ensure market price is within our limit
            if (is_sell and mkt_price < order_price) or (not is_sell and mkt_price > order_price):
                break
            
            fill_quantity = min(remaining_quantity, mkt_volume)
            # Correct sign for ledger: negative if we are selling
            actual_qty = -fill_quantity if is_sell else fill_quantity
            
            # Trade constructor: (symbol, price, quantity, buyer, seller, timestamp)
            trades.append(Trade(product, mkt_price, actual_qty, "", "", t))
            remaining_quantity -= fill_quantity
            level += 1
        
        return trades, remaining_quantity

    def _fill_passive_from_trades(self, product, order, remaining_quantity, trades_df, t):
        passive_trades = []
        is_sell = order.quantity < 0
        
        if trades_df.empty or remaining_quantity <= 0:
            return passive_trades
        
        product_trades = trades_df[trades_df['product'] == product]
        
        for _, trade_row in product_trades.iterrows():
            if remaining_quantity <= 0:
                break
            
            mkt_price = int(trade_row['price'])
            mkt_volume = int(trade_row['quantity'])
            
            if (is_sell and mkt_price >= order.price) or (not is_sell and mkt_price <= order.price):
                fill_quantity = min(remaining_quantity, mkt_volume)
                actual_qty = -fill_quantity if is_sell else fill_quantity
                # Trade constructor: (symbol, price, quantity, buyer, seller, timestamp)
                passive_trades.append(Trade(product, order.price, actual_qty, "", "", t))
                remaining_quantity -= fill_quantity
        
        return passive_trades

    def match_engine(self, prices, orders, trades_df=None, timestamp=None):
        fills = {}
        for product, order_list in orders.items():
            product_price_rows = prices[prices['product'] == product]
            if product_price_rows.empty: continue
            product_prices = product_price_rows.iloc[0]

            for order in order_list:
                remaining_quantity = abs(order.quantity)
                is_sell = order.quantity < 0
                
                # Aggressive
                prefix = 'bid' if is_sell else 'ask'
                aggressive_trades, remaining_quantity = self._fill_order_across_levels(
                    product, product_prices, remaining_quantity, prefix, order.price, is_sell, timestamp
                )
                fills.setdefault(product, []).extend(aggressive_trades)
                
                # Passive
                if remaining_quantity > 0 and trades_df is not None:
                    passive = self._fill_passive_from_trades(product, order, remaining_quantity, trades_df, timestamp)
                    fills.setdefault(product, []).extend(passive)
        return fills

    def update_ledger(self, fills):
        for product, trades in fills.items():
            if product not in self.current_position:
                self.current_position[product] = 0
                self.own_trades[product] = []

            for trade in trades:
                self.current_position[product] += trade.quantity
                self.current_cash -= trade.price * trade.quantity
                self.own_trades[product].append(trade)

# Run test
backtester = Backtester(Trader, prices_df, pd.DataFrame())
backtester.run()