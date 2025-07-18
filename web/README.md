# MaybeBot Web Dashboard

A professional web interface for configuring and managing your MaybeBot Discord server.

## 🌟 Features

- **Discord OAuth2 Authentication** - Secure login with Discord
- **Server Management** - Configure XP systems, moderation, and more
- **Real-time Analytics** - View server statistics and member activity
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Easy Configuration** - No more complex Discord commands

## 🚀 Quick Start

### 1. Discord Application Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or use your existing bot application
3. Go to **OAuth2** → **General**
4. Add redirect URI: `http://localhost:8000/auth/discord/callback`
5. Save your **Client ID** and **Client Secret**

### 2. Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration:
   ```env
   DISCORD_CLIENT_ID=your_discord_client_id
   DISCORD_CLIENT_SECRET=your_discord_client_secret
   DISCORD_BOT_TOKEN=your_discord_bot_token
   DISCORD_REDIRECT_URI=http://localhost:8000/auth/discord/callback
   JWT_SECRET_KEY=your_secret_key_here
   ```

### 3. Database Setup

The web dashboard uses the same database as your bot. Make sure your bot database is running and accessible.

### 4. Launch Dashboard

Run the launcher script:

```bash
python launch.py
```

Or manually:

```bash
# Install dependencies
pip install -r web_requirements.txt

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access Dashboard

Open your browser and go to: **http://localhost:8000**

## 📊 Dashboard Features

### Overview
- Server statistics (total members, XP, activity)
- Top member leaderboard
- Recent activity metrics

### XP System Configuration
- Enable/disable XP system
- Set XP multipliers
- Configure level-up messages
- Select announcement channels

### Moderation Settings
- Auto-moderation toggles
- Spam protection settings
- Moderation log channels

### Welcome System
- Custom welcome messages
- Welcome channel selection
- Member greeting configuration

### Server Logs
- Action logging setup
- Log channel configuration
- Event tracking settings

## 🔧 API Endpoints

The dashboard provides a REST API for programmatic access:

- `GET /api/user/me` - Get current user info
- `GET /api/guild/{guild_id}/config` - Get guild configuration
- `PUT /api/guild/{guild_id}/config` - Update guild configuration
- `GET /api/guild/{guild_id}/stats` - Get guild statistics
- `GET /api/guild/{guild_id}/channels` - Get guild channels

## 🛡️ Security

- JWT-based authentication
- Discord OAuth2 integration
- Administrator permission verification
- Secure cookie handling
- CORS protection

## 🎨 Customization

### Styling
Edit `static/style.css` to customize the dashboard appearance.

### Templates
Modify `templates/*.html` to change the dashboard layout.

### API
Extend `main.py` to add new API endpoints and features.

## 📱 Mobile Support

The dashboard is fully responsive and works great on:
- Desktop computers
- Tablets
- Mobile phones

## 🐛 Troubleshooting

### Common Issues

**Dashboard won't start:**
- Check Python installation
- Verify dependencies are installed
- Ensure .env file is configured correctly

**Login fails:**
- Verify Discord OAuth2 settings
- Check redirect URI matches exactly
- Confirm client ID and secret are correct

**Can't see servers:**
- Ensure bot is in your Discord server
- Verify you have administrator permissions
- Check bot permissions in Discord

**Database errors:**
- Confirm bot database is running
- Check database connection settings
- Verify database tables exist

### Getting Help

1. Check the console output for error messages
2. Verify your .env configuration
3. Ensure Discord OAuth2 is set up correctly
4. Check that your bot has the necessary permissions

## 🚀 Deployment

For production deployment:

1. Use a production WSGI server (gunicorn, waitress)
2. Set up SSL/HTTPS
3. Configure proper domain and redirect URIs
4. Use environment variables for secrets
5. Set up reverse proxy (nginx, apache)

Example production command:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📄 License

This web dashboard is part of MaybeBot and follows the same license terms.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Built with ❤️ for the Discord community**
