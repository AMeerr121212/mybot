import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands
import sqlite3
import datetime
import asyncio
import os

TOKEN = os.getenv("TOKEN")

VOICE_CHANNEL_ID = 1506265785243537499
AFK_CHANNEL_ID = 1506265800577777757
ROBBERY_CHANNEL_ID = 1506265812674150552

ADMIN_ROLE_IDS = [
1506661271318040616,
1506663076902994071,
1506663424287834382,
1506664397458768033,
1506664588790464552,
1506678648491737190
]

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

conn = sqlite3.connect("apex_database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
total_seconds INTEGER DEFAULT 0,
msg_count INTEGER DEFAULT 0
)
""")

conn.commit()

active_sessions = {}

def add_seconds(user_id, seconds):

```
cursor.execute(
    "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
    (user_id,)
)

cursor.execute(
    "UPDATE users SET total_seconds = total_seconds + ? WHERE user_id = ?",
    (seconds, user_id)
)

conn.commit()
```

def add_message(user_id):

```
cursor.execute(
    "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
    (user_id,)
)

cursor.execute(
    "UPDATE users SET msg_count = msg_count + 1 WHERE user_id = ?",
    (user_id,)
)

conn.commit()
```

def is_admin(member):
return any(role.id in ADMIN_ROLE_IDS for role in member.roles)

async def track_user_time(member):

```
user_id = member.id

try:

    while user_id in active_sessions:

        await asyncio.sleep(1)

        voice = member.voice

        has_game = any(
            act.type == discord.ActivityType.playing
            for act in member.activities
        )

        if not voice or not has_game:

            await asyncio.sleep(600)

            voice_check = member.voice

            game_check = any(
                act.type == discord.ActivityType.playing
                for act in member.activities
            )

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
```

class AttendanceView(View):

```
def __init__(self):
    super().__init__(timeout=None)

@discord.ui.button(
    label="تسجيل دخول",
    style=discord.ButtonStyle.green,
    custom_id="apex_on_duty"
)
async def login_button(
    self,
    interaction: discord.Interaction,
    button: Button
):

    member = interaction.user
    voice = member.voice

    has_game = any(
        act.type == discord.ActivityType.playing
        for act in member.activities
    )

    if member.id in active_sessions:

        await interaction.response.send_message(
            "🟢 أنت مسجل بالفعل.",
            ephemeral=True
        )

        return

    if (
        not voice
        or voice.channel.id != VOICE_CHANNEL_ID
        or not has_game
    ):

        await interaction.response.send_message(
            "❌ يجب أن تكون داخل الروم ومشغل Game Activity.",
            ephemeral=True
        )

        return

    active_sessions[member.id] = {
        "start_time": datetime.datetime.now(),
        "afk_seconds": 0
    }

    loop = asyncio.get_event_loop()

    active_sessions[member.id]["task"] = loop.create_task(
        track_user_time(member)
    )

    await interaction.response.send_message(
        "✅ تم تسجيل دخولك بنجاح.",
        ephemeral=True
    )

@discord.ui.button(
    label="تسجيل خروج",
    style=discord.ButtonStyle.red,
    custom_id="apex_off_duty"
)
async def logout_button(
    self,
    interaction: discord.Interaction,
    button: Button
):

    member = interaction.user

    if member.id not in active_sessions:

        await interaction.response.send_message(
            "❌ أنت غير مسجل.",
            ephemeral=True
        )

        return

    active_sessions[member.id]["task"].cancel()

    del active_sessions[member.id]

    await interaction.response.send_message(
        "🔴 تم تسجيل خروجك وحفظ ساعاتك.",
        ephemeral=True
    )
```

@bot.event
async def on_message(message):

```
if message.author.bot:
    return

if message.channel.id == ROBBERY_CHANNEL_ID:
    add_message(message.author.id)

await bot.process_commands(message)
```

@bot.tree.command(
name="setup",
description="إرسال دفتر الحضور"
)
async def setup(interaction: discord.Interaction):

```
if not is_admin(interaction.user):

    await interaction.response.send_message(
        "❌ ليس لديك صلاحية.",
        ephemeral=True
    )

    return

embed = discord.Embed(
    title="دفتر الحضور الإداري | Apex",
    description=
    "اضغط على الزر الأخضر لتسجيل الدخول.\n\n"
    "اضغط على الزر الأحمر لتسجيل الخروج.\n\n"
    "⚠️ يجب التواجد داخل الروم الصوتي "
    "ومشغل Game Activity.",
    color=discord.Color.orange()
)

await interaction.response.send_message(
    embed=embed,
    view=AttendanceView()
)
```

@bot.tree.command(
name="top",
description="توب ساعات الديوتي"
)
async def top(interaction: discord.Interaction):

```
cursor.execute("""
SELECT user_id, total_seconds
FROM users
ORDER BY total_seconds DESC
LIMIT 10
""")

data = cursor.fetchall()

embed = discord.Embed(
    title="🏆 توب ساعات الديوتي الأسبوعية",
    color=discord.Color.gold()
)

text = ""

for idx, (u_id, secs) in enumerate(data, start=1):

    hours = secs // 3600
    minutes = (secs % 3600) // 60

    text += (
        f"**{idx}-** <@{u_id}> ➔ `{hours}h {minutes}m`\n"
    )

embed.description = text or "لا توجد بيانات."

await interaction.response.send_message(embed=embed)
```

@bot.tree.command(
name="steals",
description="توب تفاعل السرقات"
)
async def steals(interaction: discord.Interaction):

```
cursor.execute("""
SELECT user_id, msg_count
FROM users
ORDER BY msg_count DESC
LIMIT 10
""")

data = cursor.fetchall()

embed = discord.Embed(
    title="💰 توب تفاعل السرقات الأسبوعي",
    color=discord.Color.green()
)

text = ""

for idx, (u_id, count) in enumerate(data, start=1):

    text += (
        f"**{idx}-** <@{u_id}> ➔ `{count}` رسالة\n"
    )

embed.description = text or "لا توجد بيانات."

await interaction.response.send_message(embed=embed)
```

@bot.event
async def on_ready():

```
print(f"Logged in as {bot.user}")

bot.add_view(AttendanceView())

await bot.tree.sync()

print("Slash Commands Synced")
```

bot.run(TOKEN)
