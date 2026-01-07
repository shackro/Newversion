# management/commands/seed_assets.py
from django.core.management.base import BaseCommand
from core.models import Asset
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed initial market assets'
    
    def handle(self, *args, **options):
        assets_data = [
            # Cryptocurrencies (10)
            {'name': 'Bitcoin', 'symbol': 'BTC', 'category': 'crypto', 'min_investment': 10, 'display_order': 1},
            {'name': 'Ethereum', 'symbol': 'ETH', 'category': 'crypto', 'min_investment': 10, 'display_order': 2},
            {'name': 'Binance Coin', 'symbol': 'BNB', 'category': 'crypto', 'min_investment': 10, 'display_order': 3},
            {'name': 'Ripple', 'symbol': 'XRP', 'category': 'crypto', 'min_investment': 10, 'display_order': 4},
            {'name': 'Cardano', 'symbol': 'ADA', 'category': 'crypto', 'min_investment': 10, 'display_order': 5},
            {'name': 'Solana', 'symbol': 'SOL', 'category': 'crypto', 'min_investment': 10, 'display_order': 6},
            {'name': 'Polkadot', 'symbol': 'DOT', 'category': 'crypto', 'min_investment': 10, 'display_order': 7},
            {'name': 'Dogecoin', 'symbol': 'DOGE', 'category': 'crypto', 'min_investment': 10, 'display_order': 8},
            {'name': 'Polygon', 'symbol': 'MATIC', 'category': 'crypto', 'min_investment': 10, 'display_order': 9},
            {'name': 'Shiba Inu', 'symbol': 'SHIB', 'category': 'crypto', 'min_investment': 10, 'display_order': 10},
            
            # Forex (6)
            {'name': 'EUR/USD', 'symbol': 'EURUSD', 'category': 'forex', 'min_investment': 50, 'display_order': 11},
            {'name': 'GBP/USD', 'symbol': 'GBPUSD', 'category': 'forex', 'min_investment': 50, 'display_order': 12},
            {'name': 'USD/JPY', 'symbol': 'USDJPY', 'category': 'forex', 'min_investment': 50, 'display_order': 13},
            {'name': 'USD/CHF', 'symbol': 'USDCHF', 'category': 'forex', 'min_investment': 50, 'display_order': 14},
            {'name': 'AUD/USD', 'symbol': 'AUDUSD', 'category': 'forex', 'min_investment': 50, 'display_order': 15},
            {'name': 'USD/CAD', 'symbol': 'USDCAD', 'category': 'forex', 'min_investment': 50, 'display_order': 16},
            
            # Futures (8)
            {'name': 'Gold Futures', 'symbol': 'XAUUSD', 'category': 'futures', 'min_investment': 100, 'display_order': 17},
            {'name': 'Silver Futures', 'symbol': 'XAGUSD', 'category': 'futures', 'min_investment': 100, 'display_order': 18},
            {'name': 'Crude Oil WTI', 'symbol': 'CL', 'category': 'futures', 'min_investment': 100, 'display_order': 19},
            {'name': 'Natural Gas', 'symbol': 'NG', 'category': 'futures', 'min_investment': 100, 'display_order': 20},
            {'name': 'S&P 500 E-mini', 'symbol': 'ES', 'category': 'futures', 'min_investment': 200, 'display_order': 21},
            {'name': 'Nasdaq 100 E-mini', 'symbol': 'NQ', 'category': 'futures', 'min_investment': 200, 'display_order': 22},
            {'name': 'Dow Jones E-mini', 'symbol': 'YM', 'category': 'futures', 'min_investment': 200, 'display_order': 23},
            {'name': 'Russell 2000 E-mini', 'symbol': 'RTY', 'category': 'futures', 'min_investment': 200, 'display_order': 24},
            
            # Stocks (6)
            {'name': 'Apple Inc.', 'symbol': 'AAPL', 'category': 'stock', 'min_investment': 50, 'display_order': 25},
            {'name': 'Tesla Inc.', 'symbol': 'TSLA', 'category': 'stock', 'min_investment': 50, 'display_order': 26},
            {'name': 'Amazon.com Inc.', 'symbol': 'AMZN', 'category': 'stock', 'min_investment': 50, 'display_order': 27},
            {'name': 'Microsoft Corp.', 'symbol': 'MSFT', 'category': 'stock', 'min_investment': 50, 'display_order': 28},
            {'name': 'Google (Alphabet)', 'symbol': 'GOOGL', 'category': 'stock', 'min_investment': 50, 'display_order': 29},
            {'name': 'NVIDIA Corp.', 'symbol': 'NVDA', 'category': 'stock', 'min_investment': 50, 'display_order': 30},
        ]
        
        for asset_data in assets_data:
            # Add initial realistic prices
            from core.services.price_fetcher import PriceFetcher
            initial_price = PriceFetcher.get_realistic_price(
                asset_data['symbol'], 
                asset_data['category']
            )
            
            asset, created = Asset.objects.get_or_create(
                symbol=asset_data['symbol'],
                defaults={
                    **asset_data,
                    'current_price': initial_price,
                }
            )
            
            if created:
                self.stdout.write(f"✓ Created {asset.name} (${initial_price})")
            else:
                self.stdout.write(f"↻ Updated {asset.name}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded 30 market assets"))