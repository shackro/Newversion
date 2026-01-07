from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    
    path('register/', views.register_view, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='auth/login.html'),name='login'),
    path('logout/',auth_views.LogoutView.as_view(),name='logout'),
    path('My-profile', views.profile, name='profile'),
    path('profile/password/', views.change_password_view, name='change_password'),
    path('settings/', views.account_settings, name='settings'),
    path('update-theme/', views.update_theme, name='update-theme'),
    
    path('', views.index, name='home'),
    path('wallet', views.wallet, name='wallet'),
    path('bonus', views.bonus_list, name='bonus'),
    
    path("switch-currency/", views.switch_currency, name="switch_currency"),
    path('number-carousel/', views.number_carousel_view, name='number_carousel'),
    path('newsletter/', views.newsletter_view, name='newsletter'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('contact/success/', views.contact_success_view, name='contact_success'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('faq/', views.faq_view, name='faq'),
    
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('claim-bonus/', views.claim_bonus, name='claim_bonus'),
    
    path('assets/', views.assets_view, name='assets'),
    path('assets/<uuid:asset_id>/', views.asset_detail, name='asset_detail'),
    path('asset/<uuid:asset_id>/invest/', views.invest_asset, name='invest_asset'),  # UUID
    path('active/', views.active_investments, name='active_investments'),
    path('history/', views.investment_history, name='history'),
    path('withdraw/<uuid:investment_id>/', views.withdraw_investment, name='withdraw'),
    
    
]
