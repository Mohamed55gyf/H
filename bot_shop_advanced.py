import discord
from discord.ext import commands
import sqlite3
import os

# إعداد قاعدة البيانات
DB_FILE = "shopverse_advanced.db"
if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, vip INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS shop (item_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS transactions (user_id INTEGER, item_name TEXT, amount INTEGER, date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS gifts (sender_id INTEGER, receiver_id INTEGER, amount INTEGER, date TEXT)")
    conn.commit()
    conn.close()

# إنشاء البوت
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# أمر إضافة عنصر إلى المتجر (للمسؤولين فقط)
@bot.command()
@commands.has_permissions(administrator=True)
async def add_item(ctx, name: str, price: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO shop (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    conn.close()
    await ctx.send(f"✅ تم إضافة العنصر **{name}** بسعر **{price} Coins** إلى المتجر!")

# أمر حذف عنصر من المتجر
@bot.command()
@commands.has_permissions(administrator=True)
async def remove_item(ctx, name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    await ctx.send(f"🗑️ تم حذف العنصر **{name}** من المتجر!")

# أمر عرض المتجر
@bot.command()
async def shop(ctx):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM shop")
    items = cursor.fetchall()
    conn.close()

    if not items:
        await ctx.send("📭 لا يوجد عناصر في المتجر حتى الآن!")
    else:
        shop_list = "
".join([f"🛒 **{item[0]}** - 💰 {item[1]} Coins" for item in items])
        await ctx.send(f"🛍 **المتجر الحالي:**
{shop_list}")

# أمر شراء عنصر
@bot.command()
async def buy(ctx, item_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT price FROM shop WHERE name = ?", (item_name,))
    item = cursor.fetchone()
    if not item:
        await ctx.send("❌ هذا العنصر غير متوفر في المتجر!")
        return

    price = item[0]
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (ctx.author.id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (ctx.author.id,))
        balance = 0
    else:
        balance = user[0]

    if balance < price:
        await ctx.send("❌ ليس لديك رصيد كافٍ لشراء هذا العنصر!")
    else:
        new_balance = balance - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, ctx.author.id))
        cursor.execute("INSERT INTO transactions (user_id, item_name, amount, date) VALUES (?, ?, ?, datetime('now'))", (ctx.author.id, item_name, price))
        conn.commit()
        await ctx.send(f"✅ لقد اشتريت **{item_name}** بنجاح! رصيدك المتبقي: **{new_balance} Coins**")

    conn.close()

# أمر تحويل عملة بين الأعضاء
@bot.command()
async def transfer(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ لا يمكنك تحويل مبلغ أقل من 1 Coin!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (ctx.author.id,))
    sender = cursor.fetchone()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (member.id,))
    receiver = cursor.fetchone()

    if not sender or sender[0] < amount:
        await ctx.send("❌ ليس لديك رصيد كافٍ للتحويل!")
    else:
        new_sender_balance = sender[0] - amount
        new_receiver_balance = (receiver[0] if receiver else 0) + amount

        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_sender_balance, ctx.author.id))
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = ?", (member.id, new_receiver_balance, new_receiver_balance))
        cursor.execute("INSERT INTO gifts (sender_id, receiver_id, amount, date) VALUES (?, ?, ?, datetime('now'))", (ctx.author.id, member.id, amount))
        conn.commit()
        await ctx.send(f"✅ تم تحويل **{amount} Coins** إلى {member.mention}!")

    conn.close()

# أمر شراء VIP
@bot.command()
async def buy_vip(ctx):
    VIP_PRICE = 1000

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, vip FROM users WHERE user_id = ?", (ctx.author.id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, vip) VALUES (?, 0, 0)", (ctx.author.id,))
        balance, vip = 0, 0
    else:
        balance, vip = user

    if vip:
        await ctx.send("❌ لديك بالفعل اشتراك VIP!")
    elif balance < VIP_PRICE:
        await ctx.send("❌ ليس لديك رصيد كافٍ لشراء اشتراك VIP!")
    else:
        new_balance = balance - VIP_PRICE
        cursor.execute("UPDATE users SET balance = ?, vip = 1 WHERE user_id = ?", (new_balance, ctx.author.id))
        conn.commit()
        await ctx.send(f"🎉 تهانينا! لقد اشتريت **اشتراك VIP** بنجاح! رصيدك المتبقي: **{new_balance} Coins**")

    conn.close()

# أمر عرض الرصيد
@bot.command()
async def balance(ctx):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (ctx.author.id,))
    user = cursor.fetchone()
    conn.close()

    balance = user[0] if user else 0
    await ctx.send(f"💰 رصيدك الحالي: **{balance} Coins**")

# تشغيل البوت
TOKEN = "YOUR_BOT_TOKEN_HERE"
bot.run(TOKEN)
