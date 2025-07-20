#!/bin/bash
# Railway startup script for Maybee Web Dashboard

echo "🚀 Starting Maybee Web Dashboard..."
echo "📁 Current directory: $(pwd)"
echo "📂 Changing to web directory..."

cd web
echo "📦 Installing dependencies..."
pip install -r requirements.txt
echo "🌐 Starting FastAPI server..."
python main.py
