# core/utils/currency.py
from decimal import Decimal
from core.models import Currency, Wallet

BASE_CURRENCY = "USD"

def get_user_currency(request):
    """
    Get user's preferred currency.
    Priority: Wallet → Cookie → USD
    """
    code = BASE_CURRENCY  # Default fallback
    
    # For authenticated users
    if request.user.is_authenticated:
        try:
            # Get wallet currency, not user.currency_preference
            wallet = Wallet.objects.get(user=request.user)
            code = wallet.currency or BASE_CURRENCY
        except Wallet.DoesNotExist:
            # If wallet doesn't exist yet, use cookie or default
            code = request.COOKIES.get('currency', BASE_CURRENCY)
        except AttributeError:
            # Fallback to cookie
            code = request.COOKIES.get('currency', BASE_CURRENCY)
    else:
        # For non-authenticated users, use cookie
        code = request.COOKIES.get('currency', BASE_CURRENCY)
    
    # Get currency object
    try:
        currency = Currency.objects.get(code=code, is_active=True)
    except Currency.DoesNotExist:
        # Fallback to USD
        currency = Currency.objects.get(code=BASE_CURRENCY)
    
    return currency

def convert_from_usd(amount, currency):
    """Convert USD amount to target currency"""
    if amount is None:
        return Decimal("0.00")
    
    try:
        amount_decimal = Decimal(str(amount))
        rate_decimal = Decimal(str(currency.exchange_rate))
        
        # If currency is USD, no conversion needed
        if currency.code == "USD":
            return amount_decimal.quantize(Decimal("0.01"))
        
        # Convert USD to target currency
        return (amount_decimal * rate_decimal).quantize(Decimal("0.01"))
    except (TypeError, ValueError, AttributeError):
        return Decimal("0.00")