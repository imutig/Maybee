# MaybeBot Deployment Guide

## 🚀 Dual Deployment Strategy

This repository contains both the Discord bot and web dashboard, deployed separately:

### 📦 Repository Structure
```
MaybeBot Official/
├── main.py              # Discord bot entry point
├── requirements.txt     # Bot dependencies
├── cog/                 # Shared bot modules
├── db.py               # Shared database module
├── web/                # Web dashboard
│   ├── main.py         # FastAPI app
│   ├── railway.toml    # Railway config
│   └── templates/      # HTML templates
└── web_requirements.txt # Web dependencies
```

## 🤖 BisectHosting (Discord Bot)

### Setup:
1. **Upload files**: All files except `web/` folder
2. **Entry point**: `main.py`
3. **Dependencies**: `requirements.txt`
4. **Environment Variables**:
   - `DISCORD_TOKEN`
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

### What it runs:
- Discord bot (`main.py`)
- Uses `cog/` modules
- Connects to database
- Handles Discord interactions

## 🌐 Railway (Web Dashboard)

### Setup:
1. **Connect GitHub repo**: Connect your repository
2. **Root directory**: Set to `web/`
3. **Start command**: `python main.py`
4. **Dependencies**: `../web_requirements.txt`
5. **Environment Variables**:
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`
   - `DISCORD_REDIRECT_URI` (https://your-app.railway.app/auth/discord/callback)
   - `DISCORD_TOKEN` (same as bot)
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - `JWT_SECRET_KEY`

### What it runs:
- FastAPI web server (`web/main.py`)
- Uses `../db.py` and `../cog/` modules
- Provides web interface
- Handles Discord OAuth

## 🔄 Auto-Updates

Both services can auto-update when you push to your repository:

### BisectHosting:
- Enable auto-restart on file changes
- Bot will restart when repository updates

### Railway:
- Auto-deploys on GitHub push
- Web dashboard updates automatically

## 🗄️ Database Sharing

Both services share the same database:
- Bot writes XP data, configurations
- Web dashboard reads/writes configurations
- Perfect synchronization between both systems

## 🔒 Environment Variables

Make sure these are set in BOTH hosting services:

### Required for Both:
```
DISCORD_TOKEN=your_bot_token
DB_HOST=your_database_host
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=your_database_name
```

### Required for Web Dashboard Only:
```
DISCORD_CLIENT_ID=your_discord_app_id
DISCORD_CLIENT_SECRET=your_discord_app_secret
DISCORD_REDIRECT_URI=https://your-railway-app.railway.app/auth/discord/callback
JWT_SECRET_KEY=your_jwt_secret_key
PORT=8000
```

## 🚀 Deployment Steps

### 1. Deploy Bot to BisectHosting:
1. Upload all files (except `web/` folder)
2. Set environment variables
3. Set entry point to `main.py`
4. Start the service

### 2. Deploy Web Dashboard to Railway:
1. Connect your GitHub repository
2. Set root directory to `web/`
3. Railway will auto-detect it's a Python app
4. Set environment variables
5. Deploy!

### 3. Configure Discord OAuth:
1. Go to Discord Developer Portal
2. Add Railway URL to redirect URIs
3. Update `DISCORD_REDIRECT_URI` environment variable

## ✅ Benefits of This Setup:

- 🔄 **Shared codebase**: Both services use the same modules
- 📦 **Single repository**: Easy to manage and update
- 🔄 **Auto-deployment**: Push once, both services update
- 📊 **Shared database**: Perfect synchronization
- 🎯 **Specialized hosting**: Each service on optimal platform
- 💰 **Cost-effective**: Use free/cheap tiers for both

## 🔧 Troubleshooting

### If web dashboard can't find modules:
- Ensure `sys.path.append('..')` is in `web/main.py`
- Check that Railway has access to parent directory files

### If Discord OAuth fails:
- Verify redirect URI matches exactly
- Check environment variables are set correctly
- Ensure bot has proper permissions

### If database connection fails:
- Verify database credentials in both services
- Check firewall/network settings
- Ensure database allows connections from both IPs
