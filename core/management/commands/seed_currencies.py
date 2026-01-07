import os
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import Currency
from core.models import Wallet

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with currencies and fix currency data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-wallets',
            action='store_true',
            help='Convert existing wallet balances from local currency to USD',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all currency data and start fresh',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("🚀 Starting currency seed script..."))
        
        if options['reset']:
            self.reset_currencies()
        
        self.seed_currencies()
        
        if options['fix_wallets']:
            self.fix_wallet_balances()
        
        self.verify_data()
        
        self.stdout.write(self.style.SUCCESS("✅ Currency seeding completed!"))

    def reset_currencies(self):
        """Reset all currency data"""
        self.stdout.write(self.style.WARNING("🔄 Resetting currency data..."))
        Currency.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("🗑️  All currencies deleted"))

    def seed_currencies(self):
        """Seed database with currencies"""
        self.stdout.write(self.style.HTTP_INFO("🌍 Seeding currencies..."))
        
        # Define all currencies with correct exchange rates and symbols
        # Exchange rate: 1 USD = X foreign currency
        currencies_data = [
            {
                'code': 'USD',
                'name': 'US Dollar',
                'symbol': '$',
                'exchange_rate': Decimal('1.0000'),
                'is_active': True,
                'is_base': True,
            },
            {
                'code': 'KES',
                'name': 'Kenyan Shilling',
                'symbol': 'KSh',
                'exchange_rate': Decimal('160.0000'),  # 1 USD = 160 KES
                'is_active': True,
                'is_base': False,
            },
            {
                'code': 'EUR',
                'name': 'Euro',
                'symbol': '€',
                'exchange_rate': Decimal('0.9200'),  # 1 USD = 0.92 EUR
                'is_active': True,
                'is_base': False,
            },
            {
                'code': 'GBP',
                'name': 'British Pound',
                'symbol': '£',
                'exchange_rate': Decimal('0.7900'),  # 1 USD = 0.79 GBP
                'is_base': False,
            },
            # {
            #     'code': 'UGX',
            #     'name': 'Ugandan Shilling',
            #     'symbol': 'USh',
            #     'exchange_rate': Decimal('3700.0000'),  # 1 USD = 3700 UGX
            #     'is_active': True,
            #     'is_base': False,
            #  },
            # {
            #     'code': 'TZS',
            #     'name': 'Tanzanian Shilling',
            #     'symbol': 'TSh',
            #     'exchange_rate': Decimal('2500.0000'),  # 1 USD = 2500 TZS
            #     'is_active': True,
            #     'is_base': False,
            # },
            # {
            #     'code': 'RWF',
            #     'name': 'Rwandan Franc',
            #     'symbol': 'RF',
            #     'exchange_rate': Decimal('1300.0000'),  # 1 USD = 1300 RWF
            #     'is_active': True,
            #     'is_base': False,
            # },
            # {
            #     'code': 'INR',
            #     'name': 'Indian Rupee',
            #     'symbol': '₹',
            #     'exchange_rate': Decimal('83.0000'),  # 1 USD = 83 INR
            #     'is_active': True,
            #     'is_base': False,
            # },
            # {
            #     'code': 'CNY',
            #     'name': 'Chinese Yuan',
            #     'symbol': '¥',
            #     'exchange_rate': Decimal('7.2000'),  # 1 USD = 7.2 CNY
            #     'is_active': True,
            #     'is_base': False,
            # },
            # {
            #     'code': 'AED',
            #     'name': 'UAE Dirham',
            #     'symbol': 'د.إ',
            #     'exchange_rate': Decimal('3.6700'),  # 1 USD = 3.67 AED
            #     'is_active': True,
            #     'is_base': False,
            # },
        ]

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for currency_data in currencies_data:
                currency, created = Currency.objects.update_or_create(
                    code=currency_data['code'],
                    defaults={
                        'name': currency_data['name'],
                        'symbol': currency_data['symbol'],
                        'exchange_rate': currency_data['exchange_rate'],
                        'is_active': currency_data.get('is_active', True),
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"  ➕ Created: {currency.code} ({currency.symbol}) - 1 USD = {currency.exchange_rate} {currency.code}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  🔄 Updated: {currency.code} ({currency.symbol}) - 1 USD = {currency.exchange_rate} {currency.code}")

        self.stdout.write(self.style.SUCCESS(f"📊 Currencies: {created_count} created, {updated_count} updated"))

    def fix_wallet_balances(self):
        """Convert existing wallet balances if they're in local currency instead of USD"""
        self.stdout.write(self.style.WARNING("💰 Fixing wallet balances..."))
        
        wallets_fixed = 0
        wallets_skipped = 0
        
        for wallet in Wallet.objects.all():
            try:
                if wallet.currency and wallet.currency != 'USD':
                    # Get the currency object
                    currency_obj = Currency.objects.get(code=wallet.currency)
                    
                    # Check if balance looks like it's in local currency (too large for USD)
                    # Example: 100,000 would be suspicious for USD but normal for KES
                    if wallet.available_balance > 1000:  # Threshold for suspicion
                        self.stdout.write(f"  ⚠️  Suspicious balance for {wallet.user.username}: {wallet.available_balance} {wallet.currency}")
                        
                        # Convert from local currency to USD
                        old_balance = wallet.available_balance
                        wallet.available_balance = wallet.available_balance / currency_obj.exchange_rate
                        wallet.locked_balance = wallet.locked_balance / currency_obj.exchange_rate if wallet.locked_balance else Decimal('0')
                        wallet.bonus_balance = wallet.bonus_balance / currency_obj.exchange_rate if wallet.bonus_balance else Decimal('0')
                        
                        # Round to 2 decimal places
                        wallet.available_balance = wallet.available_balance.quantize(Decimal('0.01'))
                        wallet.locked_balance = wallet.locked_balance.quantize(Decimal('0.01'))
                        wallet.bonus_balance = wallet.bonus_balance.quantize(Decimal('0.01'))
                        
                        wallet.save()
                        wallets_fixed += 1
                        
                        self.stdout.write(f"    🔄 Converted: {old_balance} {wallet.currency} → {wallet.available_balance} USD")
                    else:
                        wallets_skipped += 1
                else:
                    wallets_skipped += 1
                    
            except Currency.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  ❌ Currency {wallet.currency} not found for user {wallet.user.username}"))
                # Set to USD as fallback
                wallet.currency = 'USD'
                wallet.save()
                wallets_fixed += 1
        
        self.stdout.write(self.style.SUCCESS(f"💳 Wallets: {wallets_fixed} fixed, {wallets_skipped} skipped"))

    def verify_data(self):
        """Verify the seeded data"""
        self.stdout.write(self.style.HTTP_INFO("🔍 Verifying data..."))
        
        # Check currencies
        currencies = Currency.objects.filter(is_active=True)
        self.stdout.write(f"  📈 Active currencies: {currencies.count()}")
        
        for currency in currencies:
            self.stdout.write(f"    • {currency.code}: {currency.symbol} - 1 USD = {currency.exchange_rate}")
        
        # Check wallets
        wallets = Wallet.objects.all()
        usd_wallets = wallets.filter(currency='USD')
        other_wallets = wallets.exclude(currency='USD')
        
        self.stdout.write(f"  👛 Total wallets: {wallets.count()}")
        self.stdout.write(f"    • USD wallets: {usd_wallets.count()}")
        self.stdout.write(f"    • Other currency wallets: {other_wallets.count()}")
        
        # Show sample balances
        sample_wallet = wallets.first()
        if sample_wallet:
            self.stdout.write(f"  🧪 Sample wallet ({sample_wallet.user.username}):")
            self.stdout.write(f"    • Currency: {sample_wallet.currency}")
            self.stdout.write(f"    • Balance: {sample_wallet.available_balance}")
            self.stdout.write(f"    • Equity: {sample_wallet.locked_balance}")
        
        # Verify conversion
        usd = Currency.objects.get(code='USD')
        kes = Currency.objects.get(code='KES')
        
        test_amount = Decimal('100')
        converted = test_amount * kes.exchange_rate
        
        self.stdout.write(f"  🧮 Conversion test:")
        self.stdout.write(f"    • {test_amount} USD = {converted} KES")
        self.stdout.write(f"    • Expected: {test_amount} × {kes.exchange_rate} = {converted}")