import pandas as pd
import matplotlib.pyplot as plt
from engine.datamodel import *
from pandas import DataFrame as df

# Standard IMC Limits
LIMITS = {
    "EMERALDS": 20, "TOMATOES": 20, "STARFISH": 20, "ORCHIDS": 100,
    "CHOCOLATE": 250, "STRAWBERRIES": 250, "ROSES": 60, "GIFT_BASKET": 60,
    "COCONUT": 200, "COCONUT_COUPON": 600,
    "PEARLS": 20, "BANANAS": 20 # These 2 just for my tests
}

class Backtester:
    def __init__(self, Trader, prices_df: df, trades_df: df):
        self.trader = Trader() if isinstance(Trader, type) else Trader
        self.prices_df = prices_df
        self.trades_df = trades_df

        self.products = self.prices_df['product'].unique()
        self.current_position = {product: 0 for product in self.products}
        self.own_trades = {product: [] for product in self.products}
        self.current_cash = 0
        self.last_trader_data = ""
        self.history = [] 

    def run(self):
        price_groups = self.prices_df.groupby('timestamp')
        timestamps = sorted(price_groups.groups.keys())

        for t in timestamps:
            cur_time_prices = price_groups.get_group(t)
            
            # Map market trades for the TradingState
            mkt_trades = {}
            if not self.trades_df.empty:
                tick_trades = self.trades_df[self.trades_df['timestamp'] == t]
                for p in self.products:
                    p_trades = tick_trades[tick_trades['symbol'] == p]
                    mkt_trades[p] = [Trade(p, r.price, r.quantity, "", "", t) for _, r in p_trades.iterrows()]

            # Setup state for the trader
            state_own_trades = self.own_trades.copy()
            self.own_trades = {product: [] for product in self.current_position.keys()} 

            state = TradingState(
                traderData=self.last_trader_data,
                timestamp=t,
                listings={},
                order_depths=self.get_order_depths(cur_time_prices),
                own_trades=state_own_trades,
                market_trades=mkt_trades,
                position=self.current_position,
                observations={} 
            )

            orders, conv, trader_data = self.trader.run(state)
            
            # Match engine handles limits and fills
            fills = self.match_engine(cur_time_prices, orders, mkt_trades, t)
            
            self.update_ledger(fills)
            self.last_trader_data = trader_data
            self.log_performance(t, cur_time_prices)

    def match_engine(self, prices, orders, mkt_trades, t):
        fills = {}
        for product, order_list in orders.items():
            limit = LIMITS.get(product, 20)
            curr_pos = self.current_position.get(product, 0)
            
            # Basic limit check: if the total potential buys/sells blow the limit, cancel all
            total_buy = sum(o.quantity for o in order_list if o.quantity > 0)
            total_sell = sum(o.quantity for o in order_list if o.quantity < 0)
            if curr_pos + total_buy > limit or curr_pos + total_sell < -limit:
                continue

            product_price_rows = prices[prices['product'] == product]
            if product_price_rows.empty: continue
            prod_row = product_price_rows.iloc[0]

            for order in order_list:
                remaining = abs(order.quantity)
                is_sell = order.quantity < 0
                
                # 1. Aggressive: Match against the order book
                prefix = 'bid' if is_sell else 'ask'
                agg_trades, remaining = self._fill_order_across_levels(
                    product, prod_row, remaining, prefix, order.price, is_sell, t
                )
                fills.setdefault(product, []).extend(agg_trades)

                # 2. Passive: Match against market trades (the jmerle way)
                if remaining > 0 and product in mkt_trades:
                    for m_trade in mkt_trades[product]:
                        if remaining <= 0: break
                        # If market traded at or better than our limit price, we get filled
                        if (is_sell and m_trade.price >= order.price) or (not is_sell and m_trade.price <= order.price):
                            qty = min(remaining, abs(m_trade.quantity))
                            actual_qty = -qty if is_sell else qty
                            fills.setdefault(product, []).append(Trade(product, order.price, actual_qty, "", "", t))
                            remaining -= qty
        return fills

    def _fill_order_across_levels(self, product, prod_row, remaining_qty, price_prefix, order_price, is_sell, t):
        trades = []
        for level in range(1, 4): # Check levels 1, 2, and 3
            if remaining_qty <= 0: break
            
            p_col, v_col = f'{price_prefix}_price_{level}', f'{price_prefix}_volume_{level}'
            if p_col not in prod_row or pd.isna(prod_row[p_col]): break

            mkt_price, mkt_vol = int(prod_row[p_col]), abs(int(prod_row[v_col]))
            
            # Stop if the market price isn't within our limit
            if (is_sell and mkt_price < order_price) or (not is_sell and mkt_price > order_price):
                break
            
            fill_qty = min(remaining_qty, mkt_vol)
            actual_qty = -fill_qty if is_sell else fill_qty
            trades.append(Trade(product, mkt_price, actual_qty, "", "", t))
            remaining_qty -= fill_qty
        
        return trades, remaining_qty

    def update_ledger(self, fills):
        for product, trades in fills.items():
            for trade in trades:
                self.current_position[product] += trade.quantity
                self.current_cash -= trade.price * trade.quantity
                self.own_trades[product].append(trade)

    def get_order_depths(self, prices):
        order_depths = {}
        for _, row in prices.iterrows():
            bids, asks = {}, {}
            asset = row["product"]
            orders = OrderDepth()
            for col in prices.columns:
                if pd.isna(row[col]) or row[col] == 0: continue
                if col.startswith("bid_price"):
                    vol_col = col.replace("price", "volume")
                    if vol_col in row and row[vol_col] != 0:
                        self.add_volume(bids, int(row[col]), int(row[vol_col]))
                elif col.startswith("ask_price"):
                    vol_col = col.replace("price", "volume")
                    if vol_col in row and row[vol_col] != 0:
                        self.add_volume(asks, int(row[col]), -1*int(row[vol_col]))   
            orders.buy_orders, orders.sell_orders = bids, asks
            order_depths[asset] = orders
        return order_depths

    def add_volume(self, order_dict, price, volume):
        order_dict[price] = order_dict.get(price, 0) + volume

    def log_performance(self, t, prices_at_t):
        stats = {'timestamp': t, 'cash': self.current_cash}
        total_value = self.current_cash
        for product in self.products:
            pos = self.current_position.get(product, 0)
            stats[f'{product}_pos'] = pos
            prod_row = prices_at_t[prices_at_t['product'] == product]
            if not prod_row.empty:
                mid = (prod_row.iloc[0]['bid_price_1'] + prod_row.iloc[0]['ask_price_1']) / 2
                item_value = pos * mid
                total_value += item_value
        stats['total_pnl'] = total_value
        self.history.append(stats)

    def plot_performance(self):
        df_history = pd.DataFrame(self.history)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        ax1.plot(df_history['timestamp'], df_history['total_pnl'], color='green')
        ax1.set_title('Total PnL')
        for product in self.products:
            ax2.plot(df_history['timestamp'], df_history[f'{product}_pos'], label=product)
        ax2.legend()
        plt.show()