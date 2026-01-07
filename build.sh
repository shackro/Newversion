#!/bin/bash
echo "🚀 Starting Vercel build process..."

# Install Python dependencies
pip install -r requirements.txt

# Create static directory if it doesn't exist
mkdir -p static

# Create a simple favicon to avoid errors
echo '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💰</text></svg>">' > static/favicon.ico

# Create robots.txt
echo 'User-agent: *' > static/robots.txt
echo 'Disallow:' >> static/robots.txt

# Collect static files
python manage.py collectstatic --noinput

echo "✅ Build completed!"