from backtester import Backtester
import pandas as pd
from tutorial.tutorial import Trader

prices_df = pd.read_csv('tutorial/data/prices_round_0_day_-1.csv', delimiter=';')
trades_df = pd.read_csv('tutorial/data/trades_round_0_day_-1.csv', delimiter=';')

trader = Trader()

# Run test
backtester = Backtester(trader, prices_df, pd.DataFrame())
backtester.run()

# See the results
print(f"Final Cash: {backtester.current_cash}")
print(f"Final Positions: {backtester.current_position}")
backtester.plot_performance()