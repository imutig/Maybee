# 🐝 Maybee - Advanced Discord Bot with Web Dashboard

<div align="center">

[![GitHub release](https://img.shields.io/github/release/imutig/Maybee.svg?style=for-the-badge)](https://github.com/imutig/Maybee/releases)
[![GitHub stars](https://img.shields.io/github/stars/imutig/Maybee.svg?style=for-the-badge)](https://github.com/imutig/Maybee/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/imutig/Maybee.svg?style=for-the-badge)](https://github.com/imutig/Maybee/issues)
[![License](https://img.shields.io/github/license/imutig/Maybee.svg?style=for-the-badge)](LICENSE)

[![Discord](https://img.shields.io/badge/Discord-Bot-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Web%20Dashboard-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MySQL](https://img.shields.io/badge/MySQL-Database-4479a1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)

**A comprehensive, high-performance Discord bot with a professional web dashboard for complete server management.**

*Sweet server management, honey! 🍯*

</div>

## 🌟 Overview

**Maybee** is a modern, feature-rich Discord bot designed for comprehensive server management with enterprise-grade reliability. Built with cutting-edge technologies and featuring a professional web dashboard, it offers both Discord commands and web-based configuration for ultimate flexibility.

### 🚀 Key Highlights

- **🌐 Professional Web Dashboard** - Beautiful, responsive interface for bot configuration
- **🔄 Dual Management** - Configure via Discord commands OR web dashboard
- **📊 Advanced Analytics** - Real-time server statistics and member insights
- **🛡️ Complete Moderation Suite** - Warnings, timeouts, and comprehensive logging
- **🏆 Gamification System** - XP/leveling with multipliers and leaderboards
- **🌍 Multi-language Support** - English and French translations
- **⚡ High Performance** - Optimized architecture with connection pooling and caching

## 🏗️ Architecture & Technologies

### Core Technologies
- **Python 3.11+** with asyncio optimization
- **discord.py 2.3+** with full slash command support
- **FastAPI** for the web dashboard with JWT authentication
- **MySQL** with connection pooling for enterprise-grade data persistence
- **Service container** with dependency injection
- **Health monitoring** with real-time metrics and performance profiling

### Performance Features
- **Database connection pooling** (1-10 configurable connections)
- **Batch XP processing** (50+ updates per batch for 95% performance improvement)
- **Intelligent caching** with TTL and persistent storage
- **Background task optimization** with proper cleanup
- **Memory-efficient data structures** and automatic cleanup routines

### Security & Reliability
- **JWT-based authentication** with Discord OAuth2 integration
- **Input validation and sanitization** for all user inputs
- **Permission-based access control** with role validation
- **Rate limiting protection** (global + command-specific)
- **Comprehensive logging** with structured format
- **Automatic error recovery** with graceful degradation

## 🌐 Web Dashboard Features

### 🎯 Modern Interface
- **Discord OAuth2 Authentication** - Secure login with your Discord account
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **Real-time Configuration** - Changes sync instantly with the bot
- **Professional UI** - Clean, intuitive interface with modern design
- **Test Functions** - Preview messages before sending them live

### 📊 Dashboard Capabilities
- **Server Statistics** - Member count, XP totals, activity metrics
- **XP System Management** - Configure multipliers, channels, and level-up messages
- **Welcome System** - Customize welcome and goodbye messages
- **Server Logs** - Configure detailed event logging with granular controls
- **Moderation Tools** - Manage warnings, timeouts, and mod actions
- **Channel Management** - Easy channel selection for all features

### 🔧 Configuration Systems
- **XP System**: Enable/disable, set multipliers, configure announcement channels
- **Welcome Messages**: Custom messages with variables, separate welcome/goodbye channels
- **Server Logs**: Granular control over 12+ event types with dedicated log channels
- **Moderation**: Automated tools with customizable settings
- **Language Settings**: Multi-language support with per-server preferences

## 🗄️ Database Architecture

Comprehensive MySQL database with optimized tables for maximum performance:

| Table | Purpose | Features |
|-------|---------|----------|
| `xp_data` | User XP and levels | Optimized indexing, batch updates |
| `xp_history` | XP gain tracking | Historical data for analytics |
| `xp_config` | XP system settings | Per-server configuration |
| `welcome_config` | Welcome/goodbye messages | Rich message customization |
| `server_logs_config` | Event logging settings | Granular event control |
| `guild_config` | General server settings | Centralized configuration |
| `warnings` | Moderation warnings | Full audit trail |
| `timeouts` | Timeout history | Duration and reason tracking |
| `role_requests` | Role request system | Approval workflow |
| `confessions` | Anonymous confessions | Privacy-focused design |
| `user_languages` | Language preferences | Per-user localization |

## ✨ Core Features

### 🏆 Advanced XP System
- **Intelligent XP Gains**: Text messages (10s cooldown) and voice activity (10min intervals)
- **Configurable Multipliers**: Server-wide XP multipliers for balanced progression
- **Comprehensive Leaderboards**: Weekly, monthly, and all-time rankings
- **Detailed Statistics**: `/xpstats` with historical data and activity insights
- **Automatic Role Rewards**: Level-based role assignment
- **Custom Announcements**: Configurable level-up messages with dedicated channels
- **Multiple XP Types**: Separate tracking for text, voice, and total XP
- **Persistent Cache**: High-performance leaderboards that survive restarts

### 🛡️ Complete Moderation Suite
- **Warning System**: `/warn` with reasons and full history tracking
- **Timeout Management**: `/timeout` and `/untimeout` with duration controls
- **Moderation History**: `/warnings` to view user's complete record
- **Audit Trail**: Complete database logging of all moderation actions
- **Permission Controls**: Role-based access to moderation commands
- **Automated Cleanup**: `/clearwarnings` for fresh starts

### 🎭 Advanced Role Management
- **Role Requests**: `/role add/remove` with approval workflow
- **Interactive Approvals**: Button-based interface for administrators
- **Role Statistics**: `/rolestats` for tracking approved/rejected requests
- **Persistent Buttons**: Interfaces work even after bot restarts
- **Role Reactions**: Emoji-based role assignment with `/rolereact`
- **Multi-role Support**: Configure multiple roles per reaction message

### 👋 Welcome & Goodbye System
- **Custom Messages**: Personalized welcome and goodbye messages
- **Dynamic Variables**: `{user}`, `{server}`, `{memberName}`, `{memberMention}`
- **Separate Channels**: Different channels for welcome and goodbye messages
- **Rich Embeds**: Beautiful, colorful embeds with user avatars
- **Web Configuration**: Easy setup through web dashboard or Discord commands

### 📋 Comprehensive Server Logs
- **12+ Event Types**: Member joins/leaves, message edits/deletes, role changes, voice activity
- **Granular Control**: Enable/disable specific event types
- **Rich Logging**: Detailed embeds with timestamps, user information, and context
- **Dedicated Channels**: Separate log channels for organized monitoring
- **Real-time Monitoring**: Instant notifications for server events

### 💬 Additional Features
- **Anonymous Confessions**: Private confession system with statistics
- **Ticket System**: Support ticket creation with automated categorization
- **Multi-language Support**: English and French with per-user preferences
- **Utility Commands**: Avatar display, dice rolling, member scanning
- **Meeting Organization**: Schedule and manage server meetings
- **Custom Embeds**: Create rich embed messages with `/embed`

## 🎮 Command Reference

### 👤 User Commands
| Command | Description |
|---------|-------------|
| `/ping` | Check bot latency and response time |
| `/avatar [user]` | Display user's avatar in high resolution |
| `/level` | View your current level and XP progress |
| `/leaderboard [period] [type]` | View server leaderboards (weekly/monthly/all-time) |
| `/xpstats [user]` | Detailed XP statistics with historical data |
| `/roll` | Roll a dice (1-100) |
| `/confession <message>` | Send an anonymous confession |
| `/role add/remove <role>` | Request role addition or removal |

### 🛡️ Moderation Commands
| Command | Permission | Description |
|---------|------------|-------------|
| `/warn <user> <reason>` | Moderate Members | Issue a warning with reason |
| `/timeout <user> <duration> <reason>` | Moderate Members | Temporarily timeout a user |
| `/untimeout <user>` | Moderate Members | Remove timeout from user |
| `/warnings [user]` | Moderate Members | View warning history |
| `/clearwarnings <user>` | Moderate Members | Clear user's warnings |
| `/clear <number>` | Manage Messages | Delete multiple messages |
| `/rename <user> <name>` | Manage Nicknames | Change user's nickname |

### ⚙️ Configuration Commands
| Command | Permission | Description |
|---------|------------|-------------|
| `/config` | Administrator | **Unified configuration interface** |
| `/setup_ticket` | Administrator | Configure ticket system |
| `/rolereact` | Administrator | Set up role reaction system |

### 📊 Statistics Commands
| Command | Permission | Description |
|---------|------------|-------------|
| `/confessionstats` | Manage Messages | View confession statistics |
| `/rolestats` | Manage Roles | View role request statistics |
| `/levelroles` | - | List all level-based roles |
| `/cachestats` | Administrator | System cache performance |

## 🔧 Configuration System

### 🎯 Unified `/config` Command
The `/config` command provides a centralized interface for all bot settings:

- **🎉 Welcome System**: Configure welcome/goodbye messages and channels
- **💬 Confessions**: Set up anonymous confession channels
- **🎭 Role Requests**: Configure role request approval channels
- **🏆 XP System**: Manage XP settings, multipliers, and announcement channels
- **📋 Server Logs**: Configure detailed event logging
- **🎫 Ticket System**: Set up support ticket categories
- **🌍 Language**: Choose server language (English/French)

### 🌐 Web Dashboard Configuration
Access the same configuration options through the web dashboard:
- **Real-time sync** with Discord bot
- **Test functions** to preview messages
- **Visual channel selection** with dropdown menus
- **Instant validation** and error handling
- **Mobile-responsive** interface

## 🚀 Deployment

### 🔄 Dual Hosting Architecture
Maybee uses a sophisticated dual-hosting setup for optimal performance:

**Discord Bot (BisectHosting):**
- Runs the main Discord bot (`main.py`)
- Handles all Discord interactions
- Processes commands and events
- Manages database operations

**Web Dashboard (Railway):**
- Hosts the FastAPI web interface
- Provides Discord OAuth2 authentication
- Offers web-based configuration
- Shares the same database for perfect sync

### 🔒 Environment Configuration
Both services require these environment variables:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token

# Database Configuration  
DB_HOST=your_database_host
DB_USER=your_database_user
DB_PASS=your_database_password
DB_NAME=your_database_name

# Web Dashboard Only
DISCORD_CLIENT_ID=your_discord_app_id
DISCORD_CLIENT_SECRET=your_discord_app_secret
DISCORD_REDIRECT_URI=https://your-app.railway.app/auth/discord/callback
JWT_SECRET_KEY=your_jwt_secret_key
```

### 🛠️ Database Requirements
- **MySQL Server** (local or cloud)
- **Database created** (bot creates tables automatically)
- **User permissions**: CREATE, SELECT, INSERT, UPDATE, DELETE
- **Connection pooling** supported for high performance

## 📊 Performance Metrics

### 🚀 Optimization Features
- **95% performance improvement** with batch XP processing
- **Connection pooling** reduces database overhead
- **Intelligent caching** for frequently accessed data
- **Persistent leaderboards** survive bot restarts
- **Memory-efficient** data structures
- **Background task optimization** with proper cleanup

### 📈 Scalability
- **Multi-server support** with isolated data
- **Concurrent user handling** with asyncio
- **Database indexing** for fast queries
- **Rate limiting** to prevent abuse
- **Graceful error handling** with automatic recovery

## 🌍 Multi-language Support

### 🗣️ Available Languages
- **English** (default)
- **French** (français)

### 🎯 Language Features
- **Per-user preferences**: Each user can choose their language
- **Per-server defaults**: Server-wide language settings
- **Complete translation**: All commands, messages, and interfaces
- **Web dashboard**: Fully translated web interface
- **Dynamic switching**: Change language anytime with `/config`

## 🔐 Security Features

### 🛡️ Authentication & Authorization
- **JWT-based authentication** with secure token handling
- **Discord OAuth2 integration** for trusted login
- **Administrator permission verification** for sensitive actions
- **Role-based access control** with permission checks
- **Secure cookie handling** with proper expiration

### 🔒 Data Protection
- **Input validation** and sanitization for all user inputs
- **SQL injection prevention** with parameterized queries
- **Rate limiting** to prevent abuse and spam
- **Comprehensive logging** for security auditing
- **Privacy-focused design** for sensitive features like confessions

## 🐛 Troubleshooting

### Common Issues

**Bot not responding:**
- Check if bot is online and has proper permissions
- Verify environment variables are set correctly
- Check database connection and credentials

**Web dashboard login fails:**
- Verify Discord OAuth2 configuration
- Check redirect URI matches exactly
- Confirm client ID and secret are correct

**Commands not working:**
- Ensure bot has required permissions in server
- Check if command cooldowns are active
- Verify user has necessary permissions

**Database errors:**
- Confirm MySQL server is running
- Check database connection settings
- Verify database user has proper permissions

### 📞 Support
- **Creator**: iMutig
- **Discord**: iMutig#0444
- **GitHub**: Create an issue in the repository
- **Documentation**: Check code comments and this README

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

<div align="center">

**🐝 Developed with ❤️ by iMutig**

*Making Discord server management sweet as honey! 🍯*

[![Discord](https://img.shields.io/badge/Contact-iMutig%230444-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)

</div>
