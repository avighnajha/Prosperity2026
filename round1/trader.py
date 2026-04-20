from engine.datamodel import OrderDepth, TradingState, Order
import json

LIMITS = {
    "ASH_COATED_OSMIUM": 250, 
    "INTARIAN_PEPPER_ROOT": 250
}

class Trader:
    def get_new_trader_data(self, history):
        return json.dumps(history)

    def run(self, state: TradingState):
        result = {}
        # Load history from traderData string
        history = json.loads(state.traderData) if state.traderData else {"INTARIAN_PEPPER_ROOT": []}
        
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            current_pos = state.position.get(product, 0)
            
            if product == "ASH_COATED_OSMIUM":
                # OSMIUM: Stable 10k
                fair_value = 10000
                snipe_orders, new_pos = self.snipe(product, order_depth, fair_value, current_pos)
                maker_orders = self.market_make(product, order_depth, fair_value, new_pos)
                result[product] = snipe_orders + maker_orders

            elif product == "INTARIAN_PEPPER_ROOT":
                mid_price = self.get_mid(order_depth)
                
                if mid_price is not None:
                    history[product].append(mid_price)
                    if len(history[product]) > 20: 
                        history[product].pop(0)

                if len(history[product]) > 0:
                    fair_value = sum(history[product]) / len(history[product])
                    
                    snipe_orders, new_pos = self.snipe(product, order_depth, fair_value, current_pos)
                    result[product] = snipe_orders
                else:
                    print(f"Skipping {product} at timestamp {state.timestamp} - No price data yet.")
                    result[product] = []

        return result, 0, self.get_new_trader_data(history)

    def get_mid(self, order_depth):
        # Check if we actually have bids and asks
        if not order_depth.buy_orders or not order_depth.sell_orders:
            # If one side is missing, we can't calculate a mid. 
            # Return None or a dummy value (we will handle this in the logic)
            return None
        
        best_ask = min(order_depth.sell_orders.keys())
        best_bid = max(order_depth.buy_orders.keys())
        return (best_ask + best_bid) / 2

    def snipe(self, product, order_depth, fair_value, current_pos):
        orders = []
        limit = LIMITS[product]

        sorted_asks = sorted(order_depth.sell_orders.items()) # Low to High
        for price, vol in sorted_asks:
            if price < fair_value and current_pos < limit:
                buy_qty = min(abs(vol), limit - current_pos)
                orders.append(Order(product, price, buy_qty))
                current_pos += buy_qty
        
        sorted_bids = sorted(order_depth.buy_orders.items(), reverse=True) # High to Low
        for price, vol in sorted_bids:
            if price > fair_value and current_pos > -limit:
                sell_qty = min(vol, limit + current_pos)
                orders.append(Order(product, price, -sell_qty))
                current_pos -= sell_qty

        return orders, current_pos

    def market_make(self, product, order_depth, fair_value, current_pos):
        orders = []
        limit = LIMITS[product]
        
        bid_price = int(fair_value - 1)
        ask_price = int(fair_value + 1)

        if current_pos < limit:
            orders.append(Order(product, bid_price, limit - current_pos))
        if current_pos > -limit:
            orders.append(Order(product, ask_price, -(limit + current_pos)))

        return orders