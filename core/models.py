from datetime import datetime, timedelta
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

from pesaprime import settings

class User(AbstractUser):
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=100, default='Kenya')
    currency_preference = models.CharField(max_length=10, default='KES')
    theme_preference = models.CharField(max_length=10, default='light')
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} - {self.phone}"

class Verification(models.Model):
    VERIFICATION_TYPES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('identity', 'Identity Verification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    token = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ['user', 'verification_type']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    risk_tolerance = models.CharField(max_length=20, default='medium', 
                                      choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    investment_goals = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"
    

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    currency_preference = models.CharField(max_length=10, default="USD")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    available_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    locked_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonus_claimed = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')  # Add this for currency preference

    def __str__(self):
        return f"{self.user.username} Wallet"

    def total_balance(self):
        return self.available_balance + self.locked_balance + self.bonus_balance


class Transaction(models.Model):
    # Transaction types
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    INVESTMENT = 'investment'
    PROFIT = 'profit'
    BONUS = 'bonus'
    ADJUSTMENT = 'adjustment'
    
    TRANSACTION_TYPE_CHOICES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (INVESTMENT, 'Investment'),
        (PROFIT, 'Profit'),
        (BONUS, 'Bonus'),
        (ADJUSTMENT, 'Adjustment'),
    ]
    
    # Payment methods
    MPESA = 'mpesa'
    CARD = 'card'
    BANK = 'bank'
    WALLET = 'wallet'
    
    PAYMENT_METHOD_CHOICES = [
        (MPESA, 'M-Pesa'),
        (CARD, 'Credit/Debit Card'),
        (BANK, 'Bank Transfer'),
        (WALLET, 'Wallet Balance'),
    ]
    
    # Status
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (COMPLETED, 'Completed'),
    ]

    # Fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')  # Changed
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='wallet_transactions') 
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default=DEPOSIT)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=MPESA)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    
    reference = models.CharField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} | {self.amount} | {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"TX{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
        

class Asset(models.Model):
    CATEGORY_CHOICES = [
        ('crypto', 'Cryptocurrency'),
        ('forex', 'Forex'),
        ('futures', 'Futures'),
        ('stock', 'Stock'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Price data
    current_price = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    previous_price = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    change_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Investment settings
    min_investment = models.DecimalField(max_digits=20, decimal_places=2, default=10)
    max_investment = models.DecimalField(max_digits=20, decimal_places=2, default=100000)
    
    # Last updated timestamp
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Display ordering
    display_order = models.PositiveIntegerField(default=0)
    
    icon = models.ImageField(upload_to='assets/icons/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    return_rate_1h = models.DecimalField(max_digits=5, decimal_places=2, default=0.5)  # 0.5% per hour
    return_rate_3h = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)  # 1.5% per 3 hours
    return_rate_6h = models.DecimalField(max_digits=5, decimal_places=2, default=3.0)  # 3.0% per 6 hours
    return_rate_12h = models.DecimalField(max_digits=5, decimal_places=2, default=6.0)  # 6.0% per 12 hours
    return_rate_24h = models.DecimalField(max_digits=5, decimal_places=2, default=12.0)  # 12.0% per 24 hours
    
    # Risk level
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('very_high', 'Very High Risk'),
    ]
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='medium')
    
    # Allowed investment durations (in hours)
    allowed_durations = models.JSONField(default=list)  # Store as list: [1, 3, 6, 12, 24]
    
    def get_return_rate(self, duration_hours):
        """Get return rate for a specific duration"""
        rates = {
            1: self.return_rate_1h,
            3: self.return_rate_3h,
            6: self.return_rate_6h,
            12: self.return_rate_12h,
            24: self.return_rate_24h,
        }
        return rates.get(duration_hours, Decimal('0.0'))
    
    def calculate_profit(self, invested_amount, duration_hours):
        """Calculate potential profit for an investment"""
        return_rate = self.get_return_rate(duration_hours)
        return (invested_amount * return_rate) / 100
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
    def update_price(self, new_price):
        """Update price and calculate changes"""
        if self.current_price and new_price:
            self.previous_price = self.current_price
            self.current_price = new_price
            self.change_percentage = ((self.current_price - self.previous_price) / self.previous_price) * 100
        elif new_price:
            self.current_price = new_price
        self.save()
    
    def needs_update(self):
        """Check if price needs update (older than 5 minutes)"""
        if not self.last_updated:
            return True
        update_threshold = datetime.now() - timedelta(minutes=5)  # FIXED: Use timedelta
        return self.last_updated < update_threshold
    
    def get_icon_url(self):
        """Get icon URL or default"""
        if self.icon:
            return self.icon.url
        # Default icons based on category
        defaults = {
            'crypto': '/static/assets/crypto.png',
            'forex': '/static/assets/forex.png',
            'futures': '/static/assets/futures.png',
            'stock': '/static/assets/stock.png',
        }
        return defaults.get(self.category, '/static/assets/default.png')
    


class Investment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset = models.ForeignKey('core.Asset', on_delete=models.CASCADE)
    
    invested_amount = models.DecimalField(max_digits=20, decimal_places=2)
    duration_hours = models.PositiveIntegerField(default=3)
    
    # Time tracking
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Returns
    expected_return_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    actual_profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0.0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.asset.name} - {self.invested_amount}"
    
    def save(self, *args, **kwargs):
        if not self.end_time and self.duration_hours:
            self.end_time = self.start_time + timezone.timedelta(hours=self.duration_hours)
        
        if not self.expected_return_rate and self.asset and self.duration_hours:
            self.expected_return_rate = self.asset.get_return_rate(self.duration_hours)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if investment has expired"""
        if self.status != 'active':
            return False
        return timezone.now() >= self.end_time
    
    @property
    def time_remaining(self):
        """Get time remaining in hours"""
        if self.status != 'active':
            return 0
        remaining = self.end_time - timezone.now()
        return max(0, remaining.total_seconds() / 3600)  # Convert to hours
    
    @property
    def expected_profit(self):
        """Calculate expected profit"""
        return (self.invested_amount * self.expected_return_rate) / 100
    
    def complete_investment(self):
        """Complete the investment and calculate actual profit"""
        if self.status != 'active':
            return
        
        # Simulate profit/loss based on market conditions
        import random
        from decimal import Decimal
        
        # Base profit based on expected return
        base_profit = self.expected_profit
        
        # Add some randomness (±20%)
        random_factor = Decimal(str(random.uniform(0.8, 1.2)))
        self.actual_profit_loss = base_profit * random_factor
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Update user's wallet
        wallet = self.user.wallet
        total_amount = self.invested_amount + self.actual_profit_loss
        
        wallet.locked_balance -= self.invested_amount
        wallet.available_balance += total_amount
        wallet.save()
        
        # Create transaction record
        
        Transaction.objects.create(
            user=self.user,
            wallet=wallet,
            transaction_type='profit',
            payment_method='system',
            amount=self.actual_profit_loss,
            status='completed',
            description=f"Profit from {self.asset.name} investment"
        )
        
        return self.actual_profit_loss
    


class Bonus(models.Model):
    """Bonus system for users"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='bonuses'  # This creates user.bonuses
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    TYPE_CHOICES = [
        ('welcome', 'Welcome Bonus'),
        ('deposit', 'Deposit Bonus'),
        ('referral', 'Referral Bonus'),
        ('promotion', 'Promotional Bonus'),
    ]
    
    bonus_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='promotion')
    is_claimed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Bonuses'    
    
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.subject} - {self.name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'