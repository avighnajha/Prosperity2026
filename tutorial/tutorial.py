import json

from engine.datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

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
        
            # Snipe any bad orders
            snipe_orders, current_position = self.snipe(product, order_depth, fair_value, current_position)
            orders.extend(snipe_orders)

            # Market making
            make_orders, current_position = self.make(product, order_depth, fair_value, current_position)
            orders.extend(make_orders)

                
    
        traderData = self.compress_data()
        conversions = 0
        return result, conversions, traderData
    
    def snipe(self, product, order_depth, fair_value, current_position):
        pass

    def make(self, product, order_depth, fair_value, current_position):
        pass

    def decompress_data(self, data_string: str):
        if not data_string:
            return {} # First tick, memory is empty
        return json.loads(data_string)
    
    def compress_data(self, history_dict: dict):
        return json.dumps(history_dict)