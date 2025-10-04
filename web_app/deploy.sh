#!/bin/bash

# DigitalOcean App Platform Deployment Script

echo "🚀 Deploying Deck Compress Web App to DigitalOcean..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI not found. Please install it first:"
    echo "   https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if logged in
if ! doctl account get &> /dev/null; then
    echo "❌ Not logged in to DigitalOcean. Please run: doctl auth init"
    exit 1
fi

# Deploy the app
echo "📦 Deploying app..."
doctl apps create-deployment deck-compress-web-app

echo "✅ Deployment initiated! Check the DigitalOcean dashboard for progress."
echo "🔗 Your app will be available at the URL shown in the dashboard."
