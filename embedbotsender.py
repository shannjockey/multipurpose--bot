import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix='!ss', intents=intents, help_command=None)

STAFF_ROLE_ID = 1390879993516789861
TICKET_CATEGORY_ID = 1387239034794803230
TICKET_LOG_CHANNEL_ID = 1387985690528317551

ticket_message_logs = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name.startswith("ticket-"):
        if message.channel.id not in ticket_message_logs:
            ticket_message_logs[message.channel.id] = []
        timestamp = message.created_at.strftime("%H:%M:%S")
        ticket_message_logs[message.channel.id].append((timestamp, message.author.display_name, message.content))

    await bot.process_commands(message)

async def log_ticket_action(guild, user, channel_name, action, message_log=None):
    log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title=f"Ticket {action}",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Channel", value=channel_name, inline=False)

        if message_log:
            log_text = "\n".join(f"({ts}) {author}: {content}" for ts, author, content in message_log)
            if len(log_text) > 1024:
                embed.add_field(name="Chat Log (partial)", value=f"```\n{log_text[:1020]}...\n```", inline=False)
                await log_channel.send(embed=embed)
                await log_channel.send(f"```\n{log_text[1020:]}\n```")
            else:
                embed.add_field(name="Chat Log", value=f"```\n{log_text}\n```", inline=False)

        await log_channel.send(embed=embed)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        ticket_owner_name = channel.name[len("ticket-"):].replace("-", " ")

        if (staff_role in user.roles) or (user.name.lower() == ticket_owner_name.lower()):
            await interaction.response.send_message("Closing ticket...", ephemeral=True)
            message_log = ticket_message_logs.pop(channel.id, [])
            closed_time = datetime.datetime.utcnow().strftime("%H:%M:%S")
            message_log.append((closed_time, "Ticket", "Closed"))
            await log_ticket_action(guild, user, channel.name, "Closed", message_log)
            await channel.delete()
        else:
            await interaction.response.send_message("Only the ticket owner or staff can close this ticket.", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message("❌ You already have a ticket open.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}".replace(" ", "-").lower(),
            overwrites=overwrites,
            category=category
        )

        ticket_message_logs[channel.id] = []
        staff_role = guild.get_role(STAFF_ROLE_ID)

        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=(
                f"{user.mention}, {staff_role.mention} will be with you shortly.\n\n"
                "When you're done, click the **Close Ticket** button below to close this ticket."
            ),
            color=discord.Color.blue()
        )
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        await log_ticket_action(guild, user, channel.name, "Created")

@bot.command()
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎟️ Support Tickets",
        description="Need help? Click the button below to create a private ticket. Staff will assist you shortly.",
        color=discord.Color.orange()
    )
    embed.set_footer(text="Developer = @shannjockey!")
    embed.set_thumbnail(url="https://i.imgur.com/Qys8KcJ.png")

    await ctx.send(embed=embed, view=TicketView())

@bot.command()
async def applypanel(ctx):
    embed = discord.Embed(
        title="📝 Skygen/Discord Staff Application!",
        description="""Click the link(s) below to apply!
***Requirements:***
• 13+ Years old  
• SPaG at all times

📌 **In-Game Application**  
[__Apply Here__](https://docs.google.com/forms/d/e/1FAIpQLSeBGToFyw94cUy32qhNKl1AJfgucb8impgq4KkK9OBak0VsAw/viewform?usp=sharing&ouid=109199441440511430799)

📌 **Discord Application**  
[__Apply Here__](https://docs.google.com/forms/d/e/1FAIpQLSfcr-lxszpLOSVB9-CQBCKGNNvhPiM9LUlwjhoMd3JNX13eFg/viewform?usp=sharing&ouid=109199441440511430799)
""",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Developer = @shannjockey!") 
    embed.set_thumbnail(url="https://i.imgur.com/Qys8KcJ.png")
    await ctx.send(embed=embed)

@bot.command()
async def bothelp(ctx):
    embed = discord.Embed(
        title="🛠️ Bot Help",
        description="""
**!ssapplypanel** — Sends the Skygen/Discord staff application panel.  
**!ssticketpanel** — Sends a ticket creation panel.

More commands coming soon!
""",
        color=discord.Color.green()
    )
    embed.set_footer(text="Developer = @shannjockey!")
    embed.set_thumbnail(url="https://i.imgur.com/Qys8KcJ.png")
    await ctx.send(embed=embed)

# 🔐 Replace 'MTM..' with your bot token!

bot.run("MTM5OTE2NjA3ODI4NTc3NTA1MA.GY5XhD.Ovj7YNwtSKT2xEoRB7aY9nU6FzEoRxSZKkQ634")
