from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404, render

# Create your views here.
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

from core.services.price_fetcher import PriceFetcher
from .models import Asset, Currency, Transaction, UserProfile,Wallet
from core.models import Investment
from core.utils.currency import convert_from_usd, get_user_currency
from .forms import ContactForm, DepositForm, PasswordChangeForm, ProfileUpdateForm, RegisterForm, UserUpdateForm, WithdrawalForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(request, 'Account created successfully.')
            return redirect('home')

    return render(request, 'auth/register.html', {'form': form})


@login_required
def profile(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get currency from context processor (already available in template)
    # But we need it for calculations
    currency = get_user_currency(request)
    
    # Get user's wallet
    try:
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance = convert_from_usd(wallet.available_balance, currency)
        wallet_equity = convert_from_usd(wallet.locked_balance, currency)
        wallet_total = convert_from_usd(wallet.total_balance(), currency)
    except Wallet.DoesNotExist:
        wallet_balance = Decimal('0')
        wallet_equity = Decimal('0')
        wallet_total = Decimal('0')
        wallet = None
    
    # Get investment stats
    investments = Investment.objects.filter(user=request.user)
    
    # Calculate total invested
    total_invested_usd = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    total_invested = convert_from_usd(total_invested_usd, currency)
    
    # Calculate total profit/loss
    total_profit_loss_usd = investments.aggregate(
        total=Sum('actual_profit_loss')
    )['total'] or Decimal('0')
    total_profit_loss = convert_from_usd(total_profit_loss_usd, currency)
    
    # Handle form submissions
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'wallet': wallet,
        'wallet_balance': wallet_balance,
        'wallet_equity': wallet_equity,
        'wallet_total': wallet_total,
        'total_invested': total_invested,
        'total_profit_loss': total_profit_loss,
        'profile': profile,
        # Currency data is added by context_processor automatically
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def account_settings(request):
    """
    Reserved for future:
    - Change password
    - Update email
    - KYC
    """
    return render(request, 'auth/settings.html')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            
            if user.check_password(current_password):
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('profile')
            else:
                form.add_error('current_password', 'Current password is incorrect.')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


@csrf_exempt
def update_theme(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        theme = data.get('theme')
        request.user.profile.theme = theme  # assuming user has profile with theme field
        request.user.profile.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def switch_currency(request):
    if request.method == "POST":
        code = request.POST.get("currency")
        try:
            currency = Currency.objects.get(code=code, is_active=True)
            
            # Update user's wallet currency preference
            wallet = Wallet.objects.get(user=request.user)
            wallet.currency = currency.code
            wallet.save()
            
            # Set cookie for consistency
            response = redirect(request.META.get("HTTP_REFERER", "/"))
            response.set_cookie('currency', currency.code, max_age=30*24*60*60)
            return response
            
        except Currency.DoesNotExist:
            # If currency doesn't exist, redirect without changes
            pass
    
    return redirect(request.META.get("HTTP_REFERER", "/"))

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

@login_required
def index(request):
    """Main dashboard with assets preview"""
    # Get or create wallet
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),  # Give some starting balance
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    if created:
        messages.info(request, 'Welcome! Your wallet has been created')
    
    currency = get_user_currency(request)
    
    # =========================
    # WALLET CONVERSION (USD → selected currency)
    # =========================
    wallet_data = {
        'available': convert_from_usd(wallet.available_balance, currency),
        'locked': convert_from_usd(wallet.locked_balance, currency),
        'bonus': convert_from_usd(wallet.bonus_balance, currency),
        'total': convert_from_usd(wallet.total_balance(), currency),
    }
    

    # =========================
    # INVESTMENTS
    # =========================
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    )
    
    completed_investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active')
    
    # =========================
    # PnL CALCULATION (USD → currency) - FIXED
    # =========================
    total_profit_usd = completed_investments.filter(
        actual_profit_loss__gt=0  # ✅ FIXED: Changed profit_loss to actual_profit_loss
    ).aggregate(total=Sum('actual_profit_loss'))['total'] or Decimal('0')  # ✅ FIXED
    
    total_loss_usd = completed_investments.filter(
        actual_profit_loss__lt=0  # ✅ FIXED: Changed profit_loss to actual_profit_loss
    ).aggregate(total=Sum('actual_profit_loss'))['total'] or Decimal('0')  # ✅ FIXED
    
    net_pl_usd = total_profit_usd + total_loss_usd
    
    invested_total_usd = completed_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    
    net_pl_percentage = (
        (net_pl_usd / invested_total_usd) * 100
        if invested_total_usd > 0 else 0
    )
    
    # =========================
    # CONVERT PnL TO USER'S CURRENCY
    # =========================
    investment_stats = {
        'total_profit': convert_from_usd(total_profit_usd, currency),
        'total_loss': convert_from_usd(total_loss_usd, currency),
        'net_pl': convert_from_usd(net_pl_usd, currency),
        'net_pl_percentage': round(net_pl_percentage, 2),
        'progress_width': min(abs(net_pl_percentage), 100),
        'active_investments': active_investments.count(),
    }
    
    # =========================
    # TRANSACTIONS - CRITICAL FIX
    # =========================
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Convert transaction amounts for display
    for transaction in recent_transactions:
        # Store both the original amount and converted amount
        transaction.original_amount = transaction.amount  # USD amount
        transaction.display_amount = convert_from_usd(transaction.amount, currency)  # Converted amount
        transaction.display_currency_symbol = currency.symbol
    
    # =========================
    # MARKET ASSETS FOR DASHBOARD (4-6 featured assets)
    # =========================
    from .models import Asset
    
    # Get top 6 active assets (mix of categories)
    market_assets = Asset.objects.filter(is_active=True).order_by('?')[:8]
    
    # Add display prices in user's currency
    for asset in market_assets:
        asset.display_price = convert_from_usd(asset.current_price, currency)
        asset.display_min_investment = convert_from_usd(asset.min_investment, currency)
        asset.display_max_investment = convert_from_usd(asset.max_investment, currency)
        asset.last_updated_str = asset.last_updated.strftime("%H:%M:%S") if asset.last_updated else "Never"
        
        # Add investment hours options with expected returns
        asset.ALLOWED_HOURS = [
            {'hours': 1, 'label': '1 hour', 'return_rate': asset.return_rate_1h},
            {'hours': 3, 'label': '3 hours', 'return_rate': asset.return_rate_3h},
            {'hours': 6, 'label': '6 hours', 'return_rate': asset.return_rate_6h},
            {'hours': 12, 'label': '12 hours', 'return_rate': asset.return_rate_12h},
            {'hours': 24, 'label': '24 hours', 'return_rate': asset.return_rate_24h},
        ]
        asset.duration_hours_default = 3
    
    # Calculate example returns for minimum investment
        example_investment = asset.min_investment
        asset.example_returns = {}
        for duration in asset.ALLOWED_HOURS:
            profit = asset.calculate_profit(example_investment, duration['hours'])
            asset.example_returns[duration['hours']] = {
                'profit_usd': profit,
                'profit_display': convert_from_usd(profit, currency),
                'total_usd': example_investment + profit,
                'total_display': convert_from_usd(example_investment + profit, currency),
            }
            
    # =========================
    # INVESTMENT FORM
    # =========================
    from django import forms
    
    class QuickInvestmentForm(forms.Form):
        """Quick investment form for dashboard"""
        amount = forms.DecimalField(
            max_digits=20,
            decimal_places=2,
            min_value=Decimal('10.00'),
            widget=forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm',
                'placeholder': f'Min: {currency.symbol}10.00',
                'step': '0.01'
            })
        )
        
        duration_hours = forms.ChoiceField(
            choices=[(1, '1 hour'), (3, '3 hours'), (6, '6 hours'), (12, '12 hours'), (24, '24 hours')],
            initial=3,
            widget=forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm'
            })
        )
    
    investment_form = QuickInvestmentForm()
    
    context = {
        'wallet': wallet_data,
        'investment_stats': investment_stats,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'recent_transactions': recent_transactions,
        'market_assets': market_assets,
        'investment_form': investment_form,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'available_currencies': Currency.objects.filter(is_active=True),
        'current_currency': currency,
    }
    
    return render(request, 'home.html', context)



@login_required
def profile(request):
    """
    User profile page.
    NO financial logic here.
    """
    user = request.user

    context = {
        'user': user,
    }

    return render(request, 'accounts/profile.html', context)


    
@login_required
def wallet(request):
    # FIX: Get or create wallet
    user_wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    currency = get_user_currency(request)
    
    # =========================
    # WALLET CONVERSION (USD → selected currency)
    # =========================
    # Use the SAME field names as in your dashboard view
    wallet_data = {
        'available': convert_from_usd(user_wallet.available_balance, currency),
        'locked': convert_from_usd(user_wallet.locked_balance, currency),
        'bonus': convert_from_usd(user_wallet.bonus_balance, currency),
        'total': convert_from_usd(user_wallet.total_balance(), currency),
    }
    
    # =========================
    # INVESTMENTS
    # =========================
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    )
    
    completed_investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active')
    
    # =========================
    # PnL CALCULATION (USD → currency)
    # =========================
    total_profit_usd = completed_investments.filter(
        actual_profit_loss__gt=0  # ✅ FIXED: Changed profit_loss to actual_profit_loss
    ).aggregate(total=Sum('actual_profit_loss'))['total'] or Decimal('0')  # ✅ FIXED
    
    total_loss_usd = completed_investments.filter(
        actual_profit_loss__lt=0  # ✅ FIXED: Changed profit_loss to actual_profit_loss
    ).aggregate(total=Sum('actual_profit_loss'))['total'] or Decimal('0')  # ✅ FIXED
    
    net_pl_usd = total_profit_usd + total_loss_usd
    
    invested_total_usd = completed_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    
    net_pl_percentage = (
        (net_pl_usd / invested_total_usd) * 100
        if invested_total_usd > 0 else 0
    )
    
    # =========================
    # CONVERT PnL TO USER'S CURRENCY
    # =========================
    investment_stats = {
        'total_profit': convert_from_usd(total_profit_usd, currency),
        'total_loss': convert_from_usd(total_loss_usd, currency),
        'net_pl': convert_from_usd(net_pl_usd, currency),
        'net_pl_percentage': round(net_pl_percentage, 2),
        'progress_width': min(abs(net_pl_percentage), 100),
        'active_investments': active_investments.count(),
    }
    
    # =========================
    # TRANSACTIONS
    # =========================
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]  # Show more transactions on wallet page
    
    # Convert transaction amounts
    for transaction in recent_transactions:
        if hasattr(transaction, 'amount'):
            transaction.display_amount = convert_from_usd(transaction.amount, currency)
    
    # =========================
    # CONTEXT (Use consistent naming with dashboard)
    # =========================
    context = {
        'wallet': wallet_data,  # Same key as dashboard for consistency
        'wallet_model': user_wallet,  # The actual model instance
        'investment_stats': investment_stats,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'recent_transactions': recent_transactions,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'available_currencies': Currency.objects.filter(is_active=True),
        'current_currency': currency,
    }

    return render(request, "wallet.html", context)

def get_user_wallet(user):
    """Get or create wallet for user"""
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    return wallet

@login_required
def wallet_view(request):
    """Main wallet dashboard"""
    wallet = get_user_wallet(request.user)
    currency = get_user_currency(request)

    
    # Convert wallet balances to user's currency
    wallet_data = {
        'available': convert_from_usd(wallet.available_balance, currency),
        'locked': convert_from_usd(wallet.locked_balance, currency),
        'bonus': convert_from_usd(wallet.bonus_balance, currency),
        'total': convert_from_usd(wallet.total_balance(), currency),
        'bonus_claimed': wallet.bonus_claimed,
    }
    
    # Get transactions
    recent_deposits = Transaction.objects.filter(
        user=request.user,
        transaction_type='deposit'
    ).order_by('-created_at')[:5]
    
    recent_withdrawals = Transaction.objects.filter(
        user=request.user,
        transaction_type='withdrawal'
    ).order_by('-created_at')[:5]
    
    recent_activity = Transaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Convert transaction amounts for display
    def convert_transaction_amounts(transactions):
        for transaction in transactions:
            # transaction.amount is in USD, convert to user's currency
            transaction.display_amount = convert_from_usd(abs(transaction.amount), currency)
            
            # Add sign
            if transaction.transaction_type in ['deposit', 'profit', 'bonus']:
                transaction.display_sign = '+'
            else:
                transaction.display_sign = '-'
        return transactions
    
    recent_deposits = convert_transaction_amounts(recent_deposits)
    recent_withdrawals = convert_transaction_amounts(recent_withdrawals)
    recent_activity = convert_transaction_amounts(recent_activity)
    
    # Handle quick actions
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        action = request.POST.get('action')
        
        
        if amount <= 0:
            messages.error(request, "Please enter a valid amount")
        elif action == 'deposit':
            # User enters amount in their currency, convert to USD for storage
            amount_usd = amount / currency.exchange_rate
            
            wallet.available_balance += amount_usd
            wallet.save()
            
            # Create transaction
            Transaction.objects.create(
                user=request.user,
                wallet=wallet,
                transaction_type='deposit',
                payment_method='wallet',
                amount=amount_usd,  # Store in USD
                status='completed',
                description=f"Quick deposit of {currency.symbol}{amount:.2f}"
            )
            
            messages.success(request, f"Deposited {currency.symbol}{amount:.2f} successfully!")
            return redirect('wallet_view')  # Redirect to self
            
        elif action == 'withdraw':
            # User enters amount in their currency, convert to USD for check
            amount_usd = amount / currency.exchange_rate
            
            if wallet.available_balance >= amount_usd:
                wallet.available_balance -= amount_usd
                wallet.save()
                
                # Create transaction
                Transaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    transaction_type='withdrawal',
                    payment_method='wallet',
                    amount=-amount_usd,  # Negative for withdrawal
                    status='completed',
                    description=f"Quick withdrawal of {currency.symbol}{amount:.2f}"
                )
                
                messages.success(request, f"Withdrew {currency.symbol}{amount:.2f} successfully!")
                return redirect('wallet_view')
            else:
                messages.error(request, "Insufficient balance")
        else:
            messages.error(request, "Invalid action")
    
    context = {
        'wallet': wallet_data,
        'wallet_obj': wallet,
        'recent_deposits': recent_deposits,
        'recent_withdrawals': recent_withdrawals,
        'recent_activity': recent_activity,
        'recent_transactions': recent_activity,
        'currency': currency,
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
    }
    
    return render(request, 'wallet.html', context)

@login_required
def deposit(request):
    """Deposit page with form"""
    wallet = get_user_wallet(request.user)
    currency = get_user_currency(request)
    
    form = DepositForm(currency=currency)
    
    if request.method == 'POST':
        form = DepositForm(request.POST, currency=currency)
        
        if form.is_valid():
            amount_display = form.cleaned_data['amount']  # In user's currency
            payment_method = form.cleaned_data['payment_method']
            
            # Convert to USD for storage
            amount_usd = amount_display / currency.exchange_rate
            
            # Update wallet
            wallet.available_balance += amount_usd
            wallet.save()
            
            # Create transaction
            Transaction.objects.create(
                user=request.user,
                wallet=wallet,
                transaction_type='deposit',
                payment_method=payment_method,
                amount=amount_usd,
                status='completed',
                description=f"Deposit of {currency.symbol}{amount_display:.2f} via {payment_method}"
            )
            
            messages.success(request, f"Deposit of {currency.symbol}{amount_display:.2f} successful!")
            return redirect('wallet_view')  # Change to your actual URL
    
    context = {
        'form': form,
        'wallet_balance': convert_from_usd(wallet.available_balance, currency),
        'currency_symbol': currency.symbol,
        'current_currency': currency,
    }
    
    return render(request, 'deposit.html', context)

@login_required
def withdraw(request):
    """Withdraw page with form"""
    wallet = get_user_wallet(request.user)
    currency = get_user_currency(request)
    
    # Get recent withdrawals
    withdrawals = Transaction.objects.filter(
        user=request.user,
        transaction_type='withdrawal'
    ).order_by('-created_at')[:5]
    
    # Create quick amounts
    wallet_balance_display = convert_from_usd(wallet.available_balance, currency)
    quick_amounts = []
    
    if wallet_balance_display > 0:
        percentages = [0.25, 0.5, 0.75, 1.0]
        for perc in percentages:
            amount = (wallet_balance_display * Decimal(str(perc))).quantize(Decimal('0.01'))
            if amount >= Decimal('1.00'):
                quick_amounts.append(amount)
    
    if not quick_amounts:
        quick_amounts = [Decimal('10.00'), Decimal('50.00'), Decimal('100.00'), 
                        Decimal('200.00'), Decimal('500.00'), Decimal('1000.00')]
    
    form = WithdrawalForm(currency=currency)
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST, currency=currency)
        
        if form.is_valid():
            amount_display = form.cleaned_data['amount']  # In user's currency
            payment_method = form.cleaned_data['payment_method']
            
            # Convert to USD for storage
            amount_usd = amount_display / currency.exchange_rate
            
            if 0 < amount_usd <= wallet.available_balance:
                wallet.available_balance -= amount_usd
                wallet.save()
                
                Transaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    transaction_type='withdrawal',
                    payment_method=payment_method,
                    amount=-amount_usd,
                    status='pending',
                    description=f"Withdrawal of {currency.symbol}{amount_display:.2f} via {payment_method}"
                )
                
                messages.success(request, f"Withdrawal request of {currency.symbol}{amount_display:.2f} submitted!")
                return redirect('wallet_view')  # Change to your actual URL
            else:
                messages.error(request, "Insufficient balance")
    
    # Convert withdrawals for display
    for w in withdrawals:
        w.display_amount = convert_from_usd(abs(w.amount), currency)
    
    context = {
        'form': form,
        'wallet': wallet,
        'wallet_balance': wallet_balance_display,
        'currency_symbol': currency.symbol,
        'current_currency': currency,
        'available_balance': wallet_balance_display,
        'quick_amounts': quick_amounts,
        'withdrawals': withdrawals,
    }
    
    return render(request, 'withdraw.html', context)


@login_required
def assets_view(request):
    """Main assets page with manual price updates"""
    
    # FIX: Get or create wallet
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={
            'available_balance': Decimal('0.00'),
            'locked_balance': Decimal('0.00'),
            'bonus_balance': Decimal('0.00'),
            'bonus_claimed': Decimal('0.00'),
            'currency': 'USD'
        }
    )
    
    currency = get_user_currency(request)
    
    # Check if we should update prices
    refresh = request.GET.get('refresh', 'false').lower() == 'true'
    update_all = request.GET.get('update_all', 'false').lower() == 'true'
    
    if update_all:
        # Update all prices
        updated_count = PriceFetcher.update_all_prices()
        messages.success(request, f'Updated prices for {updated_count} assets')
        return redirect('assets')
    
    # =========================
    # WALLET SUMMARY
    # =========================
    wallet_balance = convert_from_usd(wallet.available_balance, currency)
    wallet_equity = convert_from_usd(wallet.locked_balance, currency)
    
    user_investments = Investment.objects.filter(user=request.user)
    
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    )
    
    completed_investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active')
    
    total_invested_usd = user_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    total_invested = convert_from_usd(total_invested_usd, currency)
    
    total_profit_usd = completed_investments.filter(
        actual_profit_loss__gt=0  # ✅ FIXED: Changed profit_loss to actual_profit_loss
    ).aggregate(total=Sum('actual_profit_loss'))['total'] or Decimal('0')  # ✅ FIXED
    
    total_loss_usd = completed_investments.filter(
        actual_profit_loss__lt=0  # ✅ FIXED: Changed profit_loss to actual_profit_loss
    ).aggregate(total=Sum('actual_profit_loss'))['total'] or Decimal('0')  # ✅ FIXED
    
    net_pl_usd = total_profit_usd + total_loss_usd
    
    invested_total_usd = completed_investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0')
    
    net_pl_percentage = (
        (net_pl_usd / invested_total_usd) * 100
        if invested_total_usd > 0 else 0
    )
    
    # =========================
    # GET ASSETS WITH OPTIONAL UPDATE
    # =========================
    
    # Update stale prices (older than 5 minutes)
    stale_assets = Asset.objects.filter(
        is_active=True,
        last_updated__lt=datetime.now() - timedelta(minutes=5)  # FIXED: Use timedelta directly
    )[:10]  # Update max 10 at a time
    
    if stale_assets.exists() and refresh:
        for asset in stale_assets:
            PriceFetcher.update_asset_price(asset)
        messages.info(request, f'Refreshed {len(stale_assets)} stale prices')
    
    # Get all active assets
    market_assets = Asset.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # Add display prices in user's currency
    for asset in market_assets:
        asset.display_price = convert_from_usd(asset.current_price, currency)
        asset.display_min_investment = convert_from_usd(asset.min_investment, currency)
        asset.display_max_investment = convert_from_usd(asset.max_investment, currency)
        asset.last_updated_str = asset.last_updated.strftime("%H:%M:%S") if asset.last_updated else "Never"
    
    # =========================
    # CATEGORY FILTERS
    # =========================
    category = request.GET.get('category', 'all')
    if category != 'all':
        market_assets = market_assets.filter(category=category)
    
    # Group by category for the category filter
    categories = [
        {'id': 'all', 'name': 'All Assets', 'count': Asset.objects.filter(is_active=True).count()},
        {'id': 'crypto', 'name': 'Cryptocurrency', 'count': Asset.objects.filter(category='crypto', is_active=True).count()},
        {'id': 'forex', 'name': 'Forex', 'count': Asset.objects.filter(category='forex', is_active=True).count()},
        {'id': 'futures', 'name': 'Futures', 'count': Asset.objects.filter(category='futures', is_active=True).count()},
        {'id': 'stock', 'name': 'Stocks', 'count': Asset.objects.filter(category='stock', is_active=True).count()},
    ]
    
    # =========================
    # TOP GAINERS & LOSERS
    # =========================
    sorted_assets = sorted(
        market_assets,
        key=lambda x: x.change_percentage,
        reverse=True
    )
    
    top_gainers = sorted_assets[:5]
    top_losers = sorted_assets[-5:]
    
    # =========================
    # EDUCATIONAL TIPS
    # =========================
    educational_tips = [
        {
            'title': 'Click Refresh for Latest Prices',
            'content': 'Prices update automatically every 5 minutes, or click refresh for immediate updates.'
        },
        {
            'title': 'Filter by Asset Type',
            'content': 'Use the category filter to focus on specific asset classes.'
        },
        {
            'title': 'Start with Minimum Investment',
            'content': 'Begin with the minimum amount to learn before investing more.'
        },
        {
            'title': 'Watch Top Gainers/Losers',
            'content': 'Monitor these sections for market trends and opportunities.'
        }
    ]
    
    context = {
        # Wallet Summary
        'wallet_balance': wallet_balance,
        'wallet_equity': wallet_equity,
        'total_invested': total_invested,
        'total_profit_loss': total_loss_usd,
        
        # Assets Data
        'market_assets': market_assets,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'categories': categories,
        'selected_category': category,
        
        # Educational
        'educational_tips': educational_tips,
        
        # Currency
        'currency_symbol': currency.symbol,
        'currency_code': currency.code,
        'current_currency': currency,
        'available_currencies': Currency.objects.filter(is_active=True),
        
        # Refresh info
        'last_refresh': datetime.now().strftime("%H:%M:%S"),
        'stale_count': stale_assets.count(),
    }
    
    return render(request, 'assets.html', context)

@login_required
def asset_detail(request, asset_id):  # asset_id is UUID
    """View asset details for potential investment"""
    import random
    from decimal import Decimal
    from django.utils import timezone
    
    asset = get_object_or_404(Asset, id=asset_id)
    currency = get_user_currency(request)
    
    # Get user's wallet for balance display
    try:
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance_display = convert_from_usd(wallet.available_balance, currency)
    except Wallet.DoesNotExist:
        wallet_balance_display = Decimal('0.00')
    
    # Convert prices to user's currency
    current_price = getattr(asset, 'current_price', Decimal('100.00'))
    min_investment = getattr(asset, 'min_investment', Decimal('10.00'))
    max_investment = getattr(asset, 'max_investment', Decimal('10000.00'))
    
    asset.display_price = convert_from_usd(current_price, currency)
    asset.display_min_investment = convert_from_usd(min_investment, currency)
    asset.display_max_investment = convert_from_usd(max_investment, currency)
    
    # Get allowed durations and calculate expected returns
    # Use default durations if none specified
    if hasattr(asset, 'allowed_durations') and asset.allowed_durations:
        allowed_hours = asset.allowed_durations
    else:
        allowed_hours = [1, 3, 6, 12, 24]
    
    # Create duration options with returns
    duration_options = []
    for hours in allowed_hours:
        # Get return rate for this duration
        if hasattr(asset, f'return_rate_{hours}h'):
            return_rate = getattr(asset, f'return_rate_{hours}h')
        else:
            # Fallback rates based on hours
            fallback_rates = {
                1: Decimal('0.5'),
                3: Decimal('1.5'),
                6: Decimal('3.0'),
                12: Decimal('6.0'),
                24: Decimal('12.0')
            }
            return_rate = fallback_rates.get(hours, Decimal('1.0'))
        
        # Create label
        if hours == 1:
            label = "1 hour"
        elif hours < 24:
            label = f"{hours} hours"
        else:
            days = hours // 24
            label = f"{days} day{'s' if days > 1 else ''}"
        
        duration_options.append({
            'hours': hours,
            'label': label,
            'return_rate': return_rate,
            'return_percentage': return_rate,
        })
    
    # Sort by hours
    duration_options = sorted(duration_options, key=lambda x: x['hours'])
    
    # Add example calculations for minimum investment
    for option in duration_options:
        if hasattr(asset, 'calculate_profit'):
            profit_usd = asset.calculate_profit(min_investment, option['hours'])
        else:
            # Manual calculation (using Decimal)
            profit_usd = (min_investment * option['return_rate']) / Decimal('100')
        
        option['example_profit'] = {
            'usd': profit_usd,
            'display': convert_from_usd(profit_usd, currency),
            'total_usd': min_investment + profit_usd,
            'total_display': convert_from_usd(min_investment + profit_usd, currency),
        }
    
    # Get asset performance history (simulated)
    performance_history = []
    for i in range(30, 0, -1):
        # Simulate price fluctuations (convert float to Decimal)
        base_price = current_price
        fluctuation = Decimal(str(random.uniform(-0.05, 0.05)))  # Convert float to Decimal
        simulated_price = base_price * (Decimal('1') + fluctuation)
        
        performance_history.append({
            'date': timezone.now() - timezone.timedelta(days=i),
            'price': convert_from_usd(simulated_price, currency),
            'change': float(fluctuation * Decimal('100'))  # Convert to float for template
        })
    
    # Get similar assets
    similar_assets = Asset.objects.filter(
        category=asset.category,
        is_active=True
    ).exclude(id=asset.id).order_by('?')[:4]
    
    # Convert prices for similar assets
    for similar_asset in similar_assets:
        similar_asset.display_price = convert_from_usd(
            getattr(similar_asset, 'current_price', Decimal('100.00')),
            currency
        )
        similar_asset.display_min_investment = convert_from_usd(
            getattr(similar_asset, 'min_investment', Decimal('10.00')),
            currency
        )
    
    context = {
        'asset': asset,
        'currency_symbol': currency.symbol,
        'current_currency': currency,
        'wallet_balance': wallet_balance_display,
        'duration_options': duration_options,
        'performance_history': performance_history,
        'similar_assets': similar_assets,
        'default_duration': 3,  # Default selection
    }
    
    return render(request, 'investments/asset_detail.html', context)


@login_required
def invest_asset(request, asset_id):
    """Invest in a specific asset with duration"""
    if request.method == 'POST':
        asset = get_object_or_404(Asset, id=asset_id)
        currency = get_user_currency(request)
        
        try:
            # Get amount from form
            amount_display = Decimal(request.POST.get('amount', '0'))
            duration_hours = int(request.POST.get('duration_hours', 3))
            
            if amount_display <= 0:
                messages.error(request, 'Please enter a valid amount')
                return redirect('asset_detail', asset_id=asset_id)
            
            # Get user's wallet
            wallet = Wallet.objects.get(user=request.user)
            
            # Convert amount from user's currency to USD for storage
            amount_usd = amount_display / currency.exchange_rate
            
            # Check minimum investment (in USD)
            min_investment_usd = getattr(asset, 'min_investment', 10)
            if amount_usd < min_investment_usd:
                min_investment_display = convert_from_usd(min_investment_usd, currency)
                messages.error(request, f'Minimum investment is {currency.symbol}{min_investment_display:.2f}')
                return redirect('asset_detail', asset_id=asset_id)
            
            # Check if user has enough balance (compare USD to USD)
            if wallet.available_balance >= amount_usd:
                # Create investment with duration
                investment = Investment.objects.create(
                    user=request.user,
                    asset=asset,
                    invested_amount=amount_usd,
                    duration_hours=duration_hours,
                    status='active',
                    end_time=datetime.now() + timedelta(hours=duration_hours)
                )
                
                # Update wallet
                wallet.available_balance -= amount_usd
                wallet.locked_balance += amount_usd
                wallet.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    transaction_type='investment',
                    payment_method='wallet',
                    amount=-amount_usd,  # Negative for investment
                    status='completed',
                    description=f"Invested in {asset.name} for {duration_hours} hours"
                )
                
                messages.success(request, f'Successfully invested {currency.symbol}{amount_display:.2f} in {asset.name} for {duration_hours} hours')
                return redirect('assets')
            else:
                # Show helpful error message with both currencies
                available_display = convert_from_usd(wallet.available_balance, currency)
                messages.error(request, f'Insufficient balance. You have {currency.symbol}{available_display:.2f} available, trying to invest {currency.symbol}{amount_display:.2f}')
                
        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid amount specified: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('asset_detail', asset_id=asset_id)

@login_required
def withdraw_investment(request, investment_id):  # investment_id is UUID
    """Withdraw from an investment"""
    investment = get_object_or_404(Investment, id=investment_id, user=request.user)
    
    if investment.status != 'active':
        messages.error(request, 'This investment is not active')
        return redirect('active_investments')
    
    # Get user's wallet
    wallet = Wallet.objects.get(user=request.user)
    currency = get_user_currency(request)
    
    # Calculate total to withdraw (invested amount + profit)
    total_withdraw_usd = investment.invested_amount + investment.profit_loss
    
    # Update investment status
    investment.status = 'completed'
    investment.save()
    
    # Update wallet
    wallet.locked_balance -= investment.invested_amount
    wallet.balance += total_withdraw_usd
    wallet.save()
    
    total_withdraw_display = convert_from_usd(total_withdraw_usd, currency)
    messages.success(request, f'Successfully withdrew {currency.symbol}{total_withdraw_display:.2f}')
    
    return redirect('history')


@login_required
def active_investments(request):
    """View all active investments"""
    investments = Investment.objects.filter(
        user=request.user,
        status='active'
    ).select_related('asset')
    
    currency = get_user_currency(request)
    
    # Convert amounts for display
    for investment in investments:
        investment.display_invested = convert_from_usd(investment.invested_amount, currency)
        investment.display_profit = convert_from_usd(investment.profit_loss, currency)
    
    context = {
        'investments': investments,
        'currency_symbol': currency.symbol,
    }
    
    return render(request, 'investments/active.html', context)

@login_required
def investment_history(request):
    """View investment history"""
    investments = Investment.objects.filter(
        user=request.user
    ).exclude(status='active').select_related('asset')
    
    currency = get_user_currency(request)
    
    # Convert amounts for display
    for investment in investments:
        investment.display_invested = convert_from_usd(investment.invested_amount, currency)
        investment.display_profit = convert_from_usd(investment.profit_loss, currency)
    
    context = {
        'investments': investments,
        'currency_symbol': currency.symbol,
    }
    
    return render(request, 'investments/history.html', context)


@login_required
def bonus_list(request):
    user = request.user
    
    # Get currency object
    currency = get_user_currency(request)
    
    # Get wallet
    try:
        wallet = Wallet.objects.get(user=user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(
            user=user,
            available_balance=Decimal('0.00'),
            locked_balance=Decimal('0.00'),
            bonus_balance=Decimal('0.00'),
            bonus_claimed=Decimal('0.00'),
            currency='USD'
        )
    
    # Get investments - FIXED: Use the actual model name
    investments = Investment.objects.filter(user=user, status='active')
    
    total_invested = investments.aggregate(
        total=Sum('invested_amount')
    )['total'] or Decimal('0.00')
    
    # Convert total invested to user's currency
    converted_total_invested = convert_from_usd(total_invested, currency)
    
    # Get available bonuses - FIXED: Check if Bonus model exists
    try:
        # Import Bonus model if needed
        from .models import Bonus
        
        available_bonuses = Bonus.objects.filter(user=user, is_claimed=False)
        
        # Get total bonuses earned
        total_bonuses = Bonus.objects.filter(user=user, is_claimed=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
    except ImportError:
        # If Bonus model doesn't exist, create dummy data
        available_bonuses = []
        total_bonuses = Decimal('0.00')
    
    # Convert bonuses for display
    converted_available = []
    for b in available_bonuses:
        converted_available.append({
            'id': b.id,
            'title': b.title,
            'amount': convert_from_usd(b.amount, currency),
            'description': b.description,
            'bonus_type': b.get_bonus_type_display(),
        })
    
    # Convert totals
    converted_total_bonuses = convert_from_usd(total_bonuses, currency)
    converted_wallet_balance = convert_from_usd(wallet.available_balance, currency)
    
    # Calculate available balance
    wallet_balance = converted_wallet_balance - converted_total_invested
    
    # Handle bonus claiming
    if request.method == 'POST':
        bonus_id = request.POST.get('bonus_id')
        try:
            # Import Bonus model
            from .models import Bonus
            from .models import Transaction
            
            bonus = Bonus.objects.get(id=bonus_id, user=user, is_claimed=False)
            
            # Add bonus to wallet (in USD)
            wallet.available_balance += bonus.amount
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                user=user,
                wallet=wallet,
                transaction_type='bonus',
                payment_method='system',
                amount=bonus.amount,
                status='completed',
                description=f"Claimed bonus: {bonus.title}"
            )
            
            # Mark bonus as claimed
            bonus.is_claimed = True
            bonus.save()
            
            messages.success(request, f'Bonus "{bonus.title}" claimed successfully!')
            return redirect('bonus_list')
            
        except Exception as e:
            messages.error(request, f'Error claiming bonus: {str(e)}')
    
    context = {
        'wallet_balance': wallet_balance,
        'currency_symbol': currency.symbol,
        'available_bonuses': converted_available,
        'total_bonuses_earned': converted_total_bonuses,
        'currency': currency,
        'has_bonuses': len(converted_available) > 0,
    }
    
    return render(request, 'bonus.html', context)


@login_required
def claim_bonus(request):
    wallet = get_user_wallet(request.user)
    
    if not wallet.bonus_claimed:
        wallet.bonus_balance += Decimal('500.00')
        wallet.bonus_claimed = True
        wallet.save()
        
        # Create bonus transaction
        Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            transaction_type='bonus',
            payment_method='system',
            amount=Decimal('500.00'),
            status='completed',
            description="Welcome bonus claimed"
        )
        
        messages.success(request, "Bonus claimed successfully!")
    else:
        messages.warning(request, "Bonus already claimed")
    
    return redirect('wallet_view')  # Change to your actual URL

    

def number_carousel_view(request):
    # Get user's currency
    currency = get_user_currency(request)
    
    # Generate random numbers for the carousel
    import random
    numbers = []
    
    # Generate amounts in USD first, then convert to user's currency
    for _ in range(20):
        # Generate amount in USD
        amount_usd = random.randint(50, 1000)  # USD amounts
        
        # Convert to user's currency
        amount_converted = convert_from_usd(amount_usd, currency)
        
        numbers.append({
            'phone': f"+254 7{random.randint(10, 99)} xxx {random.randint(10, 99)}",
            'profit': random.choice([25, 22, -3, -43, 50, 75, -15, -30, 10, 35, -5, 60, -2, -28, 2, 90, -45, 20, -10, 45, 5, -20, 30]),
            'amount': float(amount_converted),  # Convert to float for JSON serialization
            'amount_usd': amount_usd,
            'currency_symbol': currency.symbol,
            'currency_code': currency.code,
        })
    
    return JsonResponse({'numbers': numbers})


def newsletter_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # In production, save to database or send to email service
            messages.success(request, 'Thank you for subscribing to our newsletter!')
        else:
            messages.error(request, 'Please provide a valid email address.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def about_view(request):
    return render(request, 'core/about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contact_success')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})

def contact_success_view(request):
    return render(request, 'core/contact_success.html')

def terms_view(request):
    return render(request, 'core/terms.html')

def privacy_view(request):
    return render(request, 'core/privacy.html')

def faq_view(request):
    return render(request, 'core/faq.html')
