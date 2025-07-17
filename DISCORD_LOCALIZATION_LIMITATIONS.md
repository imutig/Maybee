# Discord Slash Command Localization Limitations

## 🚫 **The Problem**

Discord's slash command system has inherent limitations regarding dynamic translations:

### **1. Command Descriptions Are Static**
- Slash command descriptions are registered **once** when the bot starts
- Discord **caches these descriptions** and doesn't allow them to change per server
- The description you see in the slash command autocomplete is **static across all servers**

### **2. Choice Names Are Static**
- `app_commands.Choice` names are also **static** and registered at startup
- They **cannot be dynamically changed** based on server language preferences
- Discord shows the **same choice names to all users** regardless of server language

### **3. Parameter Descriptions Are Static**
- `@app_commands.describe()` parameter descriptions are also **static**
- They cannot be changed based on user or server language preferences

## ✅ **What IS Possible**

### **1. Embed Content Translation** ✅
- **All embed content** (titles, fields, footers) can be translated dynamically
- **Response messages** can be fully localized
- **Error messages** can be translated
- **This is what we currently do** and it works perfectly

### **2. Discord's Built-in Localization** (Limited) ⚠️
Discord supports some built-in localization, but it has major limitations:

#### **Requirements:**
- Only works with **Discord's supported locales** (en-US, fr, de, es, etc.)
- User must have their **Discord client language** set to the target language
- **Cannot use custom server language preferences**
- Requires completely different implementation

#### **Implementation:**
```python
@app_commands.command(
    name="career",
    description="Add a career decision for a member"
)
@app_commands.locale_str("description", 
    locale=discord.Locale.french, 
    value="Ajouter une décision de carrière pour un membre"
)
```

### **3. Alternative Approaches**

#### **A. Subcommand Approach** 🔄
Instead of choices, use subcommands:
```
/career warning @user reason decided_by
/career promotion @user reason decided_by
/career demotion @user reason decided_by
```

**Pros:**
- Command names can be different per language
- More explicit and clear
- Each subcommand can have its own description

**Cons:**
- More commands to maintain
- Different user experience
- More complex implementation

#### **B. Modal/Button Approach** 🎛️
Use buttons and modals for input:
```
/career @user → Opens modal with localized interface
```

**Pros:**
- Fully localizable interface
- Rich user experience
- Complete control over translations

**Cons:**
- More complex implementation
- Different user experience
- Requires more interactions

#### **C. Auto-complete with Translation** 🔍
Use autocomplete with translated options:
```python
@app_commands.autocomplete(decision=decision_autocomplete)
async def decision_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    
    choices = [
        app_commands.Choice(
            name=_("commands.career.decisions.warning", user_id, guild_id),
            value="warning"
        ),
        app_commands.Choice(
            name=_("commands.career.decisions.promotion", user_id, guild_id),
            value="promotion"
        ),
        # ... more choices
    ]
    
    return [choice for choice in choices if current.lower() in choice.name.lower()]
```

**Pros:**
- Fully localizable choice names
- Users see translated options
- Works with current system

**Cons:**
- More complex implementation
- Requires typing to see options
- May be slower than static choices

## 🎯 **Current Implementation Analysis**

Your current `career.py` implementation is actually **optimal** given Discord's limitations:

### **What Works Well:**
✅ **Embed content is fully translated** based on user/server language
✅ **Decision names in the response** are properly localized
✅ **All visible content** to users is in their preferred language
✅ **Simple and reliable** implementation

### **What Cannot Be Translated:**
❌ Command description: "Add a career decision for a member"
❌ Parameter descriptions: "The member concerned", "Type of decision made", etc.
❌ Choice names: "Warning", "Blame", "Demotion", "Promotion", "Exclusion"

## 🔧 **Recommended Approach**

For your use case, I recommend **keeping the current implementation** because:

1. **The important content is translated** - users see localized decision names in the response
2. **Simple and reliable** - no complex workarounds needed
3. **Good user experience** - static English descriptions are acceptable for command interface
4. **Maintainable** - easy to understand and modify

### **Optional Enhancement: Autocomplete**

If you want to improve the user experience, you could add autocomplete with translated choice names:

```python
@app_commands.autocomplete(decision=decision_autocomplete)
async def career(self, interaction: discord.Interaction, ...):
    # Your existing implementation
```

This would allow users to see translated decision names when typing, while keeping the command structure simple.

## 📝 **Conclusion**

**Discord's limitations make perfect command localization impossible**, but your current implementation already handles the most important aspect: **the content users see in responses is fully translated**. The command interface being in English is a reasonable trade-off for simplicity and reliability.

If you absolutely need translated command descriptions and choices, you would need to:
1. Use Discord's built-in localization (limited to Discord's locales)
2. Or implement a modal/button-based approach
3. Or use the autocomplete approach for choice names

But for most use cases, **your current implementation is the best balance** of functionality, simplicity, and user experience.
