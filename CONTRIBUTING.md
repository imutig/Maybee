# Contributing to Maybee 🐝

Thank you for your interest in contributing to Maybee! We welcome contributions from the community.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/Maybee.git
   cd Maybee
   ```
3. **Create a new branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Set up the database:**
   ```bash
   mysql -u root -p -e 'CREATE DATABASE maybee_dev;'
   mysql -u root -p maybee_dev < database_schema.sql
   ```

## 📝 Code Guidelines

### Python Code Style
- Follow **PEP 8** style guidelines
- Use **type hints** where possible
- Write **docstrings** for all functions and classes
- Keep functions **small and focused**

### Commit Messages
Use conventional commit format:
```
feat: add new XP calculation system
fix: resolve role assignment bug
docs: update installation guide
refactor: optimize database queries
test: add unit tests for moderation system
```

### Testing
- Write tests for new features
- Ensure existing tests pass
- Test both Discord commands and web dashboard

## 🐛 Bug Reports

When reporting bugs, please include:
- **Clear description** of the issue
- **Steps to reproduce** the bug
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Error logs** if applicable

## ✨ Feature Requests

For new features:
- **Describe the feature** clearly
- **Explain the use case** and benefits
- **Consider implementation complexity**
- **Check existing issues** to avoid duplicates

## 🔄 Pull Request Process

1. **Update documentation** if needed
2. **Add/update tests** for your changes
3. **Ensure all tests pass**
4. **Update the changelog** if applicable
5. **Request review** from maintainers

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tested locally
- [ ] Added/updated tests
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## 📚 Areas for Contribution

We especially welcome contributions in:
- **Bug fixes** and stability improvements
- **New Discord features** (slash commands, interactions)
- **Web dashboard enhancements**
- **Documentation improvements**
- **Performance optimizations**
- **Internationalization** (new languages)
- **Test coverage** improvements

## 🤝 Community Guidelines

- Be **respectful** and **inclusive**
- **Help others** learn and contribute
- **Follow the code of conduct**
- **Ask questions** if you're unsure

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For general questions and ideas
- **Discord**: Join our community server (link in README)

Thank you for contributing to Maybee! 🍯
