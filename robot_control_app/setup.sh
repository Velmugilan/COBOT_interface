#!/bin/bash
set -e

echo "=== ROBOT CONTROL APP SETUP ==="

cd "$(dirname "$0")"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found."
    exit 1
fi

# 2. Check Node.js
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm not found. Please install Node.js."
    exit 1
fi

# 3. Setup Python virtual environment
echo "[INFO] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install rclpy --extra-index-url https://rospypi.github.io/Simple/

# 4. Setup Frontend
echo "[INFO] Setting up Vite frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
cd ..

echo "=== SETUP COMPLETE ==="
echo "Run the application with: python3 start_app.py"
