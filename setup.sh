#!/bin/bash

echo "==================================="
echo "Upscale AI Bootcamp Setup Script"
echo "==================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Open app.py and update the following:"
echo "   - SECRET_KEY (line 13): Replace 'your_secret_key_change_this' with a secure random string"
echo "   - PAYSTACK_SECRET_KEY (line 16): Add your Paystack secret key from https://dashboard.paystack.com/#/settings/developer"
echo ""
echo "2. Run the application:"
echo "   python3 app.py"
echo ""
echo "3. Open your browser and go to:"
echo "   http://127.0.0.1:5000/"
echo ""
echo "For test mode, use Paystack test keys (starts with sk_test_)"
echo "==================================="

