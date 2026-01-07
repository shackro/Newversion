# core/context_processors.py
from core.models import Currency, Wallet
from core.utils.currency import get_user_currency

def currency_processor(request):
    """
    Add currency data to all templates automatically.
    Returns current_currency, currency_symbol, currency_code, available_currencies
    """
    try:
        currency = get_user_currency(request)
        
        return {
            'available_currencies': Currency.objects.filter(is_active=True),
            'current_currency': currency,
            'currency_symbol': currency.symbol,
            'currency_code': currency.code,
        }
    except Exception as e:
        # Fallback to USD
        from decimal import Decimal
        
        class FallbackCurrency:
            code = 'USD'
            name = 'US Dollar'
            symbol = '$'
            exchange_rate = Decimal('1.0')
        
        return {
            'available_currencies': Currency.objects.filter(is_active=True),
            'current_currency': FallbackCurrency(),
            'currency_symbol': '$',
            'currency_code': 'USD',
        }

def get_currency_context(user):
    """Get currency context for a user"""
    try:
        wallet = Wallet.objects.get(user=user)
        currency_code = wallet.currency or "USD"
    except Wallet.DoesNotExist:
        currency_code = "USD"
    
    current_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
    if not current_currency:
        current_currency = Currency.objects.filter(is_active=True).first()

    currency_code = current_currency.code
    currency_symbol = current_currency.symbol  # FIX: Get symbol from currency object

    return wallet, currency_code, currency_symbol