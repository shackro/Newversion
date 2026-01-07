#!/bin/bash
set -e

echo "🚀 Starting Vercel build..."

# Install dependencies
pip install -r requirements.txt

# Create static directory
mkdir -p static

# Create basic favicon
echo '<link rel="icon" href="data:,">' > static/favicon.ico

# Create robots.txt
echo 'User-agent: *' > static/robots.txt
echo 'Disallow:' >> static/robots.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations if DATABASE_URL is set (PostgreSQL)
if [ -n "$DATABASE_URL" ]; then
    echo "📦 Setting up PostgreSQL database..."
    python setup_database.py
else
    echo "⚠️  No DATABASE_URL found. Skipping database setup."
fi

echo "✅ Build complete!"