#!/bin/bash
# Quick Vercel Deployment Script

echo "🚀 Email Service - Vercel Deployment Script"
echo "==========================================="
echo ""

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found!"
    echo "📦 Install it with: npm install -g vercel"
    exit 1
fi

echo "✓ Vercel CLI found"
echo ""

# Check if logged in
if ! vercel whoami &> /dev/null; then
    echo "🔐 Logging into Vercel..."
    vercel login
fi

echo "✓ Logged into Vercel"
echo ""

# Check for EMAIL_PASSWORD
echo "📧 Checking environment variables..."
if ! vercel env ls | grep -q "EMAIL_PASSWORD"; then
    echo "⚠️  EMAIL_PASSWORD not found in Vercel environment"
    echo "Please set it manually:"
    echo "  vercel env add EMAIL_PASSWORD"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit..."
fi

# Deploy
echo ""
echo "🚀 Starting deployment..."
echo ""

# Ask for deployment type
echo "Select deployment type:"
echo "1) Preview deployment (for testing)"
echo "2) Production deployment"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo "Deploying to preview..."
        vercel
        ;;
    2)
        echo "Deploying to production..."
        vercel --prod
        ;;
    *)
        echo "Invalid choice. Deploying to preview by default..."
        vercel
        ;;
esac

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Test your deployment URL"
echo "2. Check health endpoint: [URL]/health"
echo "3. View API docs: [URL]/docs"
echo "4. Test email: POST [URL]/api/v1/send-email"
