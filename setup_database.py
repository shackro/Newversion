# setup_database.py
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pesaprime.settings')
django.setup()

# Create tables if they don't exist
from django.core.management import execute_from_command_line

print("Creating database tables...")
execute_from_command_line(['manage.py', 'migrate', '--noinput'])

print("Creating default superuser...")
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Admin user created: admin / admin123")

print("Creating sample currencies...")
from core.models import Currency
from decimal import Decimal

currencies = [
    {'code': 'USD', 'name': 'US Dollar', 'symbol': '$', 'exchange_rate': Decimal('1.0')},
    {'code': 'KES', 'name': 'Kenyan Shilling', 'symbol': 'KSh', 'exchange_rate': Decimal('150.0')},
    {'code': 'EUR', 'name': 'Euro', 'symbol': '€', 'exchange_rate': Decimal('0.92')},
    {'code': 'GBP', 'name': 'British Pound', 'symbol': '£', 'exchange_rate': Decimal('0.79')},
]

for data in currencies:
    Currency.objects.get_or_create(code=data['code'], defaults=data)

print("✅ Database setup complete!")