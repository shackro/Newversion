# core/services/price_fetcher.py
import requests
from decimal import Decimal
import random
from datetime import datetime,timedelta
import logging

logger = logging.getLogger(__name__)

class PriceFetcher:
    """Fetch and simulate realistic market prices"""
    
    # Base prices for simulation (in USD)
    BASE_PRICES = {
        # Cryptocurrencies
        'BTC': 65000.00, 'ETH': 3500.00, 'BNB': 600.00, 'XRP': 0.60,
        'ADA': 0.50, 'SOL': 150.00, 'DOT': 7.00, 'DOGE': 0.15,
        'MATIC': 0.80, 'SHIB': 0.000025,
        
        # Forex
        'EURUSD': 1.08, 'GBPUSD': 1.26, 'USDJPY': 148.50,
        'USDCHF': 0.88, 'AUDUSD': 0.66, 'USDCAD': 1.35,
        
        # Futures
        'XAUUSD': 2300.00, 'XAGUSD': 26.50, 'CL': 78.00,
        'NG': 2.50, 'ES': 5200.00, 'NQ': 18000.00,
        'YM': 39000.00, 'RTY': 2000.00,
        
        # Stocks
        'AAPL': 190.00, 'TSLA': 175.00, 'AMZN': 180.00,
        'MSFT': 420.00, 'GOOGL': 155.00, 'NVDA': 950.00,
    }
    
    # Volatility factors (higher = more volatile)
    VOLATILITY = {
        'crypto': 0.03,  # 3% daily volatility
        'forex': 0.005,  # 0.5% daily volatility
        'futures': 0.01, # 1% daily volatility
        'stock': 0.015,  # 1.5% daily volatility
    }
    
    @classmethod
    def get_realistic_price(cls, symbol, category, current_price=None):
        """Generate realistic price movement"""
        base_price = cls.BASE_PRICES.get(symbol.upper())
        
        if base_price is None:
            # Fallback to random base price
            if category == 'crypto':
                base_price = random.uniform(0.01, 50000)
            elif category == 'forex':
                base_price = random.uniform(0.5, 200)
            elif category == 'futures':
                base_price = random.uniform(10, 10000)
            else:  # stocks
                base_price = random.uniform(10, 1000)
        
        # Use current price as base if available
        if current_price and current_price > 0:
            base_price = float(current_price)
        
        # Calculate realistic movement based on volatility
        volatility = cls.VOLATILITY.get(category, 0.01)
        
        # Time-based factor (mimics market hours)
        hour = datetime.now().hour
        if 9 <= hour <= 17:  # Market hours
            movement_factor = random.uniform(-volatility, volatility)
        else:
            movement_factor = random.uniform(-volatility * 0.3, volatility * 0.3)
        
        # Add some randomness
        movement_factor += random.uniform(-0.001, 0.001)
        
        # Apply movement
        new_price = base_price * (1 + movement_factor)
        
        # Ensure minimum price
        if new_price < 0.000001:
            new_price = 0.000001
        
        return Decimal(str(round(new_price, 6)))
    
    @classmethod
    def update_asset_price(cls, asset):
        """Update price for a single asset"""
        try:
            new_price = cls.get_realistic_price(
                asset.symbol, 
                asset.category,
                asset.current_price
            )
            
            asset.update_price(new_price)
            logger.info(f"Updated {asset.symbol} to ${new_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating {asset.symbol}: {str(e)}")
            return False
    
    @classmethod
    def update_all_prices(cls):
        """Update prices for all active assets"""
        from assets.models import Asset
        
        assets = Asset.objects.filter(is_active=True)
        updated_count = 0
        
        for asset in assets:
            if asset.needs_update():
                if cls.update_asset_price(asset):
                    updated_count += 1
        
        return updated_count