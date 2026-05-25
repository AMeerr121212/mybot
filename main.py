import discord
from discord.ext import commands
from discord.ui import Button, View
import sqlite3
import datetime
import asyncio
import os

TOKEN = os.getenv("TOKEN")

VOICE_CHANNEL_ID = 1506265785243537499     
AFK_CHANNEL_ID = 1506265800577777757       
ROBBERY_CHANNEL_ID = 1506265812674150552   

ADMIN_ROLE_IDS = [
    1506661271318040616, 1506663076902994071, 1506663424287834382,
    1506664397458768033, 1506664588790464552, 1506678648491737190
]

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

conn = sqlite3.connect("apex_database.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, total_seconds INTEGER DEFAULT 0, msg_count INTEGER DEFAULT 0)")
conn.commit()

active_sessions = {}

def add_seconds(user_id, seconds):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET total_seconds = total_seconds + ? WHERE user_id = ?", (seconds, user_id))
    conn.commit()

def add_message(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET msg_count = msg_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def is_admin_check(ctx):
    return any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

async def track_user_time(member):
    user_id = member.id
    try:
        while user_id in active_sessions:
            await asyncio.sleep(1)
            voice = member.voice
            has_game = any(act.type == discord.ActivityType.playing for act in member.activities)
            
            if not voice or not has_game:
                await asyncio.sleep(600)  
                voice_check = member.voice
                game_check = any(act.type == discord.ActivityType.playing for act in member.activities)
                
                if not voice_check or not game_check:
                    if user_id in active_sessions:
                        del active_sessions[user_id]
                    break
                else:
                    continue
            
            if voice.channel.id == AFK_CHANNEL_ID:
                active_sessions[user_id]["afk_seconds"] += 1
                if active_sessions[user_id]["afk_seconds"] <= 1800:
                    add_seconds(user_id, 1)
            elif voice.channel.id == VOICE_CHANNEL_ID:
                add_seconds(user_id, 1)
                
    except asyncio.CancelledError:
        pass

class AttendanceView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تسجيل دخول", style=discord.ButtonStyle.green, custom_id="apex_on_duty")
    async def login_button(self, interaction: discord.Interaction, button: Button):
        member = interaction.user
        voice = member.voice
        has_game = any(act.type == discord.ActivityType.playing for act in member.activities)
        
        if member.id in active_sessions:
            await interaction.response.send_message("أنت مسجل دخولك بالفعل! 🟢", ephemeral=True)
            return

        if not voice or voice.channel.id != VOICE_CHANNEL_ID or not has_game:
            await interaction.response.send_message("❌ يمنع تسجيل الدخول! يجب أن تكون في الفويس المعتمد ومشغل الـ Game Activity.", ephemeral=True)
            return

        active_sessions[member.id] = {"start_time": datetime.datetime.now(), "afk_seconds": 0}
        loop = asyncio.get_event_loop()
        active_sessions[member.id]["task"] = loop.create_task(track_user_time(member))
        
        await interaction.response.send_message("تم تسجيل دخولك بنجاح! طاب يومك 🟢", ephemeral=True)

    @discord.ui.button(label="تسجيل خروج", style=discord.ButtonStyle.red, custom_id="apex_off_duty")
    async def logout_button(self, interaction: discord.Interaction, button: Button):
        member = interaction.user
        if member.id not in active_sessions:
            await interaction.response.send_message("أنت غير مسجل دخولك أصلاً! 🔴", ephemeral=True)
            return
            
        active_sessions[member.id]["task"].cancel()
        del active_sessions[member.id]
        await interaction.response.send_message("تم تسجيل خروجك بنجاح وحفظ ساعاتك. 🔴", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Apex Bot Live as {bot.user.name}")
    bot.add_view(AttendanceView())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id == ROBBERY_CHANNEL_ID:
        add_message(message.author.id)
    await bot.process_commands(message)

@bot.command()
@commands.is_owner()
async def setup_apex(ctx):
    embed = discord.Embed(title="⚙️ نظام الحضور والانصراف الإداري | Apex", description="اضغط على الأزرار بالأسفل لتسجيل حضورك أو انصرافك.\n\n⚠️ **شروط الحساب:**\n1- التواجد في الروم الصوتي الأساسي.\n2- تفعيل نشاط الألعاب (Game Activity).", color=discord.Color.orange())
    await ctx.send(embed=embed, view=AttendanceView())

@bot.command(name="توب")
@commands.check(is_admin_check)
async def leaderboard(ctx):
    cursor.execute("SELECT user_id, total_seconds FROM users ORDER BY total_seconds DESC LIMIT 10")
    voice_data = cursor.fetchall()
    cursor.execute("SELECT user_id, msg_count FROM users ORDER BY msg_count DESC LIMIT 10")
    rob_data = cursor.fetchall()
    
    embed = discord.Embed(title="📊 لوحة التحكم والإحصائيات الأسبوعية | Apex", color=discord.Color.blue())
    voice_text = ""
    for idx, (u_id, secs) in enumerate(voice_data, 1):
        voice_text += f"**{idx}-** <@{u_id}> ➔ `{secs // 3600}` ساعة\n"
    embed.add_field(name="⏱️ توب ساعات الفويس (هذا الأسبوع):", value=voice_text or "لا توجد بيانات بعد.", inline=False)
    
    rob_text = ""
    for idx, (u_id, count) in enumerate(rob_data, 1):
        rob_text += f"**{idx}-** <@{u_id}> ➔ `{count}` رسالة\n"
    embed.add_field(name="💰 تفاعل روم السرقات:", value=rob_text or "لا توجد بيانات بعد.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="تصفير")
@commands.check(is_admin_check)
async def reset_weekly(ctx):
    cursor.execute("UPDATE users SET total_seconds = 0, msg_count = 0")
    conn.commit()
    await ctx.send("✅ تم تصفير إحصائيات الأسبوع بنجاح وبدء أسبوع جديد!")

bot.run(TOKEN)