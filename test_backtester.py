import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from backtester import Backtester
from engine.datamodel import OrderDepth, TradingState, Order, Trade
from tutorial.tutorial import Trader


# Helper function to create empty DataFrames with proper structure
def create_empty_prices_df():
    """Create an empty prices DataFrame with proper columns."""
    return pd.DataFrame(columns=[
        'day', 'timestamp', 'product', 'bid_price_1', 'bid_volume_1',
        'bid_price_2', 'bid_volume_2', 'bid_price_3', 'bid_volume_3',
        'ask_price_1', 'ask_volume_1', 'ask_price_2', 'ask_volume_2',
        'ask_price_3', 'ask_volume_3', 'mid_price', 'profit_and_loss'
    ])

def create_empty_trades_df():
    """Create an empty trades DataFrame with proper columns."""
    return pd.DataFrame(columns=[
        'timestamp', 'buyer', 'seller', 'product', 'currency', 'price', 'quantity'
    ])


class TestBacktesterInitialization:
    """Test Backtester initialization."""
    
    def test_init_creates_backtester_with_trader_and_dataframes(self):
        """Test that backtester initializes with correct attributes."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'timestamp': [0, 100],
            'product': ['PEARLS', 'BANANAS']
        })
        trades_df = pd.DataFrame({
            'timestamp': [50],
            'product': ['PEARLS'],
            'price': [100],
            'quantity': [10]
        })
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        assert backtester.trader == mock_trader
        assert backtester.prices_df.equals(prices_df)
        assert backtester.trades_df.equals(trades_df)
    
    def test_init_sets_default_positions_and_cash(self):
        """Test that initial positions and cash are set correctly."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        trades_df = create_empty_trades_df()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        assert backtester.current_position == {}
        assert backtester.current_cash == 0
        assert backtester.last_trader_data == ""
        assert backtester.own_trades == {}


class TestGetOrderDepths:
    """Test order depth extraction from prices."""
    
    def test_get_order_depths_parses_single_product(self):
        """Test that order depths are correctly parsed for a single product."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [10],
            'bid_price_2': [99],
            'bid_volume_2': [20],
            'ask_price_1': [102],
            'ask_volume_1': [15],
            'ask_price_2': [103],
            'ask_volume_2': [25],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        order_depths = backtester.get_order_depths(prices_df)
        
        assert 'PEARLS' in order_depths
        assert order_depths['PEARLS'].buy_orders == {100: 10, 99: 20}
        assert order_depths['PEARLS'].sell_orders == {102: -15, 103: -25}
    
    def test_get_order_depths_handles_multiple_products(self):
        """Test order depths with multiple products."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS', 'BANANAS'],
            'bid_price_1': [100, 200],
            'bid_volume_1': [10, 20],
            'ask_price_1': [102, 202],
            'ask_volume_1': [15, 25],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        order_depths = backtester.get_order_depths(prices_df)
        
        assert len(order_depths) == 2
        assert 'PEARLS' in order_depths
        assert 'BANANAS' in order_depths
    
    def test_get_order_depths_ignores_nan_values(self):
        """Test that NaN values are ignored in order depths."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [10],
            'bid_price_2': [np.nan],
            'bid_volume_2': [np.nan],
            'ask_price_1': [102],
            'ask_volume_1': [15],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        order_depths = backtester.get_order_depths(prices_df)
        
        assert len(order_depths['PEARLS'].buy_orders) == 1
        assert 100 in order_depths['PEARLS'].buy_orders
    
    def test_get_order_depths_ignores_zero_volumes(self):
        """Test that zero volumes are ignored."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [0],
            'ask_price_1': [102],
            'ask_volume_1': [15],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        order_depths = backtester.get_order_depths(prices_df)
        
        assert len(order_depths['PEARLS'].buy_orders) == 0
        assert len(order_depths['PEARLS'].sell_orders) == 1


class TestAddVolume:
    """Test volume aggregation."""
    
    def test_add_volume_new_price_level(self):
        """Test adding volume at a new price level."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        order_dict = {}
        backtester.add_volume(order_dict, 100, 10)
        
        assert order_dict[100] == 10
    
    def test_add_volume_existing_price_level(self):
        """Test aggregating volume at existing price level."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        order_dict = {100: 10}
        backtester.add_volume(order_dict, 100, 15)
        
        assert order_dict[100] == 25
    
    def test_add_volume_negative_volumes(self):
        """Test adding negative volumes (for sell orders)."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        order_dict = {}
        backtester.add_volume(order_dict, 102, -20)
        
        assert order_dict[102] == -20


class TestFillOrderAcrossLevels:
    """Test aggressive matching across price levels."""
    
    def test_fill_order_single_level_full_fill(self):
        """Test full fill from a single price level."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        product_prices = prices_df.iloc[0]
        
        # Sell order (is_sell=True, order_price=100, prefix='bid')
        trades, remaining = backtester._fill_order_across_levels('PEARLS', product_prices, 30, 'bid', 100, True, 0)
        
        assert len(trades) == 1
        assert trades[0].symbol == 'PEARLS'
        assert trades[0].price == 100
        assert trades[0].quantity == -30  # Negative for sell
        assert remaining == 0
    
    def test_fill_order_multiple_levels(self):
        """Test fill that spans multiple price levels."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [20],
            'ask_price_2': [103],
            'ask_volume_2': [30],
            'ask_price_3': [104],
            'ask_volume_3': [50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        product_prices = prices_df.iloc[0]
        
        # Buy order (is_sell=False, order_price=104, prefix='ask')
        trades, remaining = backtester._fill_order_across_levels('PEARLS', product_prices, 40, 'ask', 104, False, 0)
        
        assert len(trades) == 2
        assert trades[0].price == 102
        assert trades[0].quantity == 20  # Positive for buy
        assert trades[1].price == 103
        assert trades[1].quantity == 20
        assert remaining == 0
    
    def test_fill_order_partial_at_level(self):
        """Test partial fill when remaining quantity is less than level volume."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        product_prices = prices_df.iloc[0]
        
        # Sell order
        trades, remaining = backtester._fill_order_across_levels('PEARLS', product_prices, 100, 'bid', 100, True, 0)
        
        assert trades[0].quantity == -50  # Negative for sell
        assert remaining == 50
    
    def test_fill_order_insufficient_liquidity(self):
        """Test when there's insufficient liquidity at all levels."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [20],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        product_prices = prices_df.iloc[0]
        
        # Buy order
        trades, remaining = backtester._fill_order_across_levels('PEARLS', product_prices, 100, 'ask', 110, False, 0)
        
        assert len(trades) == 1
        assert trades[0].quantity == 20  # Positive for buy
        assert remaining == 80


class TestFillPassiveFromTrades:
    """Test passive matching against market trades."""
    
    def test_passive_fill_buy_order_matches_market_trades(self):
        """Test passive fill of buy order matching market trades below limit price."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        trades_df = pd.DataFrame({
            'product': ['PEARLS', 'PEARLS'],
            'price': [99, 100],
            'quantity': [10, 20],
        })
        
        buy_order = Order('PEARLS', 100, 25)  # Buy up to 100, want 25 units
        passive_trades = backtester._fill_passive_from_trades('PEARLS', buy_order, 25, trades_df, 0)
        
        # Should match both trades since prices <= 100
        assert len(passive_trades) == 2
        assert passive_trades[0].quantity == 10
        assert passive_trades[1].quantity == 15  # Partial fill at 100
    
    def test_passive_fill_sell_order_matches_market_trades(self):
        """Test passive fill of sell order matching market trades above limit price."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        trades_df = pd.DataFrame({
            'product': ['PEARLS', 'PEARLS'],
            'price': [101, 102],
            'quantity': [10, 20],
        })
        
        sell_order = Order('PEARLS', 101, -25)  # Sell at min 101
        passive_trades = backtester._fill_passive_from_trades('PEARLS', sell_order, 25, trades_df, 0)
        
        # Should match both trades since prices >= 101
        assert len(passive_trades) == 2
    
    def test_passive_fill_no_matching_trades(self):
        """Test when no trades match the price condition."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        trades_df = pd.DataFrame({
            'product': ['PEARLS'],
            'price': [105],
            'quantity': [10],
        })
        
        buy_order = Order('PEARLS', 100, 25)  # Want to buy up to 100
        passive_trades = backtester._fill_passive_from_trades('PEARLS', buy_order, 25, trades_df, 0)
        
        # Trade at 105 is above limit of 100, shouldn't match
        assert len(passive_trades) == 0
    
    def test_passive_fill_empty_trades_dataframe(self):
        """Test passive fill with empty trades dataframe."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        trades_df = create_empty_trades_df()
        buy_order = Order('PEARLS', 100, 25)
        passive_trades = backtester._fill_passive_from_trades('PEARLS', buy_order, 25, trades_df, 0)
        
        assert len(passive_trades) == 0


class TestMatchEngine:
    """Test the main matching engine."""
    
    def test_match_engine_aggressive_buy_order(self):
        """Test aggressive matching for buy orders."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        orders = {'PEARLS': [Order('PEARLS', 102, 30)]}
        fills = backtester.match_engine(prices_df, orders, trades_df, 0)
        
        assert 'PEARLS' in fills
        assert len(fills['PEARLS']) == 1
        assert fills['PEARLS'][0].quantity == 30  # Positive for buy
    
    def test_match_engine_aggressive_sell_order(self):
        """Test aggressive matching for sell orders."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        orders = {'PEARLS': [Order('PEARLS', 100, -30)]}
        fills = backtester.match_engine(prices_df, orders, trades_df, 0)
        
        assert 'PEARLS' in fills
        assert len(fills['PEARLS']) == 1
        assert fills['PEARLS'][0].quantity == -30  # Negative for sell
    
    def test_match_engine_partial_fill_with_passive_matching(self):
        """Test order partially filled aggressively, then passively."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [20],
        })
        trades_df = pd.DataFrame({
            'product': ['PEARLS'],
            'price': [101],
            'quantity': [15],
        })
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        orders = {'PEARLS': [Order('PEARLS', 102, 40)]}
        fills = backtester.match_engine(prices_df, orders, trades_df, 0)
        
        # Should have aggressive fill of 20 + passive fill of 15
        assert len(fills['PEARLS']) == 2
        assert sum(t.quantity for t in fills['PEARLS']) == 35
    
    def test_match_engine_multiple_orders_same_product(self):
        """Test multiple orders for the same product."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [50],
            'bid_price_1': [100],
            'bid_volume_1': [50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        orders = {
            'PEARLS': [
                Order('PEARLS', 102, 20),
                Order('PEARLS', 100, -20)
            ]
        }
        fills = backtester.match_engine(prices_df, orders, trades_df, 0)
        
        assert 'PEARLS' in fills
        assert len(fills['PEARLS']) == 2
    
    def test_match_engine_multiple_products(self):
        """Test matching for multiple products."""
        mock_trader = Mock(spec=Trader)
        prices_df = pd.DataFrame({
            'product': ['PEARLS', 'BANANAS'],
            'ask_price_1': [102, 50],
            'ask_volume_1': [50, 50],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        
        orders = {
            'PEARLS': [Order('PEARLS', 102, 20)],
            'BANANAS': [Order('BANANAS', 50, 15)],
        }
        fills = backtester.match_engine(prices_df, orders, trades_df, 0)
        
        assert 'PEARLS' in fills
        assert 'BANANAS' in fills


class TestUpdateLedger:
    """Test ledger updating."""
    
    def test_update_ledger_updates_position(self):
        """Test that update_ledger correctly updates positions."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        fills = {
            'PEARLS': [
                Trade('PEARLS', 100, 10, "", "", 0),
                Trade('PEARLS', 101, 20, "", "", 0),
            ]
        }
        
        backtester.update_ledger(fills)
        
        assert backtester.current_position['PEARLS'] == 30
        assert backtester.current_cash == -(100 * 10 + 101 * 20)
    
    def test_update_ledger_with_sell_orders(self):
        """Test ledger update with sell orders."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        fills = {
            'PEARLS': [
                Trade('PEARLS', 100, -10, "", "", 0),
            ]
        }
        
        backtester.update_ledger(fills)
        
        assert backtester.current_position['PEARLS'] == -10
        assert backtester.current_cash == -100 * -10
    
    def test_update_ledger_adds_to_own_trades(self):
        """Test that trades are added to own_trades."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        backtester.own_trades = {'PEARLS': []}
        
        fills = {
            'PEARLS': [
                Trade('PEARLS', 100, 10, "", "", 0),
            ]
        }
        
        backtester.update_ledger(fills)
        
        assert len(backtester.own_trades['PEARLS']) == 1
        assert backtester.own_trades['PEARLS'][0].quantity == 10
    
    def test_update_ledger_creates_new_product(self):
        """Test that update_ledger creates new product if not exists."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        fills = {
            'TOMATOES': [
                Trade('TOMATOES', 100, 5, "", "", 0),
            ]
        }
        
        backtester.update_ledger(fills)
        
        assert 'TOMATOES' in backtester.current_position
        assert backtester.current_position['TOMATOES'] == 5
        assert 'TOMATOES' in backtester.own_trades


class TestBacktesterRun:
    """Test the full backtester run."""
    
    def test_run_processes_all_timestamps(self):
        """Test that run processes all unique timestamps."""
        mock_trader = Mock(spec=Trader)
        mock_trader.run = Mock(return_value=({}, "", ""))
        
        prices_df = pd.DataFrame({
            'timestamp': [0, 0, 100, 100],
            'product': ['PEARLS', 'BANANAS', 'PEARLS', 'BANANAS'],
            'bid_price_1': [100, 200, 101, 201],
            'bid_volume_1': [10, 20, 10, 20],
            'ask_price_1': [102, 202, 103, 203],
            'ask_volume_1': [15, 25, 15, 25],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        backtester.run()
        
        # Trader should be called twice (one for each timestamp)
        assert mock_trader.run.call_count == 2
    
    def test_run_creates_trading_state_with_correct_timestamp(self):
        """Test that TradingState is created with correct timestamp."""
        mock_trader = Mock(spec=Trader)
        mock_trader.run = Mock(return_value=({}, "", ""))
        
        prices_df = pd.DataFrame({
            'timestamp': [0, 100],
            'product': ['PEARLS', 'PEARLS'],
            'bid_price_1': [100, 101],
            'bid_volume_1': [10, 10],
            'ask_price_1': [102, 103],
            'ask_volume_1': [15, 15],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        backtester.run()
        
        calls = mock_trader.run.call_args_list
        assert calls[0][0][0].timestamp == 0
        assert calls[1][0][0].timestamp == 100
    
    def test_run_updates_trader_data_between_timestamps(self):
        """Test that trader data is carried forward between timestamps."""
        mock_trader = Mock(spec=Trader)
        mock_trader.run = Mock(side_effect=[
            ({}, "", "trader_data_1"),
            ({}, "", "trader_data_2"),
        ])
        
        prices_df = pd.DataFrame({
            'timestamp': [0, 100],
            'product': ['PEARLS', 'PEARLS'],
            'bid_price_1': [100, 101],
            'bid_volume_1': [10, 10],
            'ask_price_1': [102, 103],
            'ask_volume_1': [15, 15],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        backtester.run()
        
        calls = mock_trader.run.call_args_list
        assert calls[0][0][0].traderData == ""
        assert calls[1][0][0].traderData == "trader_data_1"
    
    def test_run_handles_empty_trades_dataframe(self):
        """Test run with empty trades dataframe."""
        mock_trader = Mock(spec=Trader)
        mock_trader.run = Mock(return_value=({}, "", ""))
        
        prices_df = pd.DataFrame({
            'timestamp': [0],
            'product': ['PEARLS'],
            'bid_price_1': [100],
            'bid_volume_1': [10],
            'ask_price_1': [102],
            'ask_volume_1': [15],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        backtester.run()  # Should not raise
        
        assert mock_trader.run.call_count == 1
    
    def test_run_resets_own_trades_each_tick(self):
        """Test that own_trades are reset and then populated each tick."""
        mock_trader = Mock(spec=Trader)
        mock_trader.run = Mock(return_value=({}, "", ""))
        
        prices_df = pd.DataFrame({
            'timestamp': [0, 100],
            'product': ['PEARLS', 'PEARLS'],
            'bid_price_1': [100, 101],
            'bid_volume_1': [10, 10],
            'ask_price_1': [102, 103],
            'ask_volume_1': [15, 15],
        })
        trades_df = pd.DataFrame()
        
        backtester = Backtester(mock_trader, prices_df, trades_df)
        backtester.run()
        
        # Check that own_trades was reset to empty lists
        assert isinstance(backtester.own_trades['PEARLS'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

    """Test edge cases and boundary conditions."""
    
    def test_zero_quantity_order(self):
        """Test handling of zero quantity orders."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [50],
        })
        
        orders = {'PEARLS': [Order('PEARLS', 102, 0)]}
        fills = backtester.match_engine(prices_df, orders, create_empty_trades_df(), 0)
        
        assert len(fills.get('PEARLS', [])) == 0
    
    def test_no_orders_submitted(self):
        """Test match engine with no orders."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [50],
        })
        
        fills = backtester.match_engine(prices_df, {}, create_empty_trades_df(), 0)
        
        assert len(fills) == 0
    
    def test_very_large_quantity_order(self):
        """Test order with very large quantity."""
        mock_trader = Mock(spec=Trader)
        prices_df = create_empty_prices_df()
        backtester = Backtester(mock_trader, prices_df, create_empty_trades_df())
        
        prices_df = pd.DataFrame({
            'product': ['PEARLS'],
            'ask_price_1': [102],
            'ask_volume_1': [100],
            'ask_price_2': [103],
            'ask_volume_2': [100],
            'ask_price_3': [104],
            'ask_volume_3': [100],
        })
        
        orders = {'PEARLS': [Order('PEARLS', 104, 500)]}
        fills = backtester.match_engine(prices_df, orders, create_empty_trades_df(), 0)
        
        total_filled = sum(t.quantity for t in fills['PEARLS'])
        assert total_filled == 300  # All available liquidity


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
