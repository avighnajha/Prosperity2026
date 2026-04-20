#%%
from backtester import Backtester
import pandas as pd
from round1.trader import Trader

prices_df = pd.read_csv('round1/data/prices_round_1_day_-2.csv', delimiter=';')
trades_df = pd.read_csv('round1/data/trades_round_1_day_-2.csv', delimiter=';')

trader = Trader()

# Run test
backtester = Backtester(trader, prices_df, pd.DataFrame())
backtester.run()

#%%
# See the results
print(f"Final Cash: {backtester.current_cash}")
print(f"Final Positions: {backtester.current_position}")
backtester.plot_performance()