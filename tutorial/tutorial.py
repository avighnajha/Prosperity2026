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
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product == "EMERALDS":
                acceptable_price = 10000
                print("Acceptable price : " + str(acceptable_price))
                print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
        
                if len(order_depth.sell_orders) != 0:
                    # Sort keys ascending
                    sorted_asks = sorted(order_depth.sell_orders.keys())
                    best_ask = sorted_asks[0]
                    best_ask_amount = order_depth.sell_orders[best_ask]

                    print("Best ask : " + str(best_ask) + ", amount : " + str(best_ask_amount))

                    if int(best_ask) < acceptable_price:
                        print("BUY", str(-best_ask_amount) + "x", best_ask)
                        orders.append(Order(product, best_ask, -best_ask_amount))
        
                if len(order_depth.buy_orders) != 0:
                    sorted_bids = sorted(order_depth.buy_orders.keys(), reverse=True)
                    best_bid = sorted_bids[0]
                    best_bid_amount = order_depth.buy_orders[best_bid]

                    print("Best bid : " + str(best_bid) + ", amount : " + str(best_bid_amount))

                    if int(best_bid) > acceptable_price:
                        print("SELL", str(best_bid_amount) + "x", best_bid)
                        orders.append(Order(product, best_bid, -best_bid_amount))
                
                result[product] = orders
    
        traderData = ""  # No state needed - we check position directly
        conversions = 0
        return result, conversions, traderData