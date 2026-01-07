from django.contrib import admin
from .models import Asset, Investment, User, Wallet

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'phone',
        'is_active',
        'is_verified',
        'date_joined',
    )
    search_fields = ('username', 'email', 'phone')
    list_filter = ('is_active', 'is_verified')

admin.site.site_header = "InvestPro Administration"
admin.site.site_title = "InvestPro Admin"
admin.site.index_title = "Platform Control Panel"

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'available_balance', 'bonus_balance', 'bonus_claimed')
    search_fields = ('user__username',)
    

@admin.register(Asset)
class assetAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'category', 'current_price','previous_price','change_percentage','RISK_LEVEL_CHOICES')
    search_fields = ('name',)
    

@admin.register(Investment)
class InvestAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset', 'invested_amount', 'duration_hours','start_time','end_time','completed_at','expected_return_rate')
    search_fields = ('user__username',)
    
