import json

from engine.datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

LIMITS = {
    "EMERALDS": 20, "TOMATOES": 20, "STARFISH": 20, "ORCHIDS": 100,
    "CHOCOLATE": 250, "STRAWBERRIES": 250, "ROSES": 60, "GIFT_BASKET": 60,
    "COCONUT": 200, "COCONUT_COUPON": 600}

class Trader:

    def bid(self):
        return 15
    
    def run(self, state: TradingState):
        """Only method required. It takes all buy and sell orders for all
        symbols as an input, and outputs a list of orders to be sent."""

        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

        # Orders to be placed on exchange matching engine
        result = {}
        
        # LOAD STATE: Recover history from previous ticks
        # Format: {"TOMATOES": [list of prices], "EMERALDS": [list of prices]}
        history = self.decompress_data(state.traderData)
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            orders: List[Order] = []


            # Fair value calc
            if product == "EMERALDS":
                fair_value = 10000
                print("Fair value : " + str(fair_value))
                print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
            else:
                break
        
            # Snipe any bad orders
            snipe_orders, current_position = self.snipe(product, order_depth, fair_value, current_position)
            orders.extend(snipe_orders)

            # Market making
            make_orders, current_position = self.make(product, order_depth, fair_value, current_position)
            orders.extend(make_orders)

                
    
        traderData = self.compress_data(history)
        conversions = 0
        return result, conversions, traderData
    
    def snipe(self, product, order_depth, fair_value, current_position):
        orders = []
        limit = LIMITS[product]

        # Low to high
        sorted_sells = sorted(order_depth.sell_orders.items())

        for price, volume in sorted_sells:
            if price < fair_value and volume > 0:
                order_volume = min(volume, limit - current_position)
                orders.append(Order(product, price, order_volume, "SELL"))
                current_position += order_volume
            else:
                break
        
        # High to low
        sorted_buys = sorted(order_depth.buy_orders.items(), reverse=True)

        for price, volume in sorted_buys:
            if price > fair_value and volume > 0:
                order_volume = min(volume, limit + current_position)
                orders.append(Order(product, price, order_volume, "BUY"))
                current_position -= order_volume
            else:
                break

        return orders, current_position

    def make(self, product, order_depth, fair_value, current_position):
        pass

    def decompress_data(self, data_string: str):
        if not data_string:
            return {} # First tick, memory is empty
        return json.loads(data_string)
    
    def compress_data(self, history_dict: dict):
        return json.dumps(history_dict)