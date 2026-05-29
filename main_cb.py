

import os
import asyncio
import logging
import logging.handlers
import traceback
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

DISCORD_TOKEN = None
APP_ID = None
PUBLIC_KEY = None
MY_GUILD_ID = None  # temporary
OWNER_ID = None


def parse_env_file(path):
    '''Adds vars from .env file to global namespace.'''

    with open(path, "r") as file:

        print(f"parsing {path}...")

        for line in file:

            line = line.strip()
            if not line:
                continue

            key, value = line.split("=", 1)
            value = value.strip("<>")

            globals()[key] = value

            print(f"\tValue added to var: {key}")

    return True


class ThisClient(commands.Bot):
    '''Represents a client connection that connects to Discord. This class is used to interact with the Discord WebSocket and API.'''

    user: discord.ClientUser  # so the type checker won't complain

    def __init__(self, command_prefix, intents: discord.Intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def on_ready(self):
        print(f"Logged on as {self.user}. TIME:({str(datetime.now().time())})")
        print("------")

    async def on_message(self, message):
        print(f"Message from {message.author}: {message.content}")

        if message.author.bot:
            return

        await self.process_commands(message)

    async def setup_hook(self):

        if not MY_GUILD:
            raise RuntimeError("Guild ID is missing!")

        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        #  self.my_background_task.start()

    @tasks.loop(seconds=60)
    async def my_background_task(self):
        #  for channel in self.get_all_channels():
        print("Loop works!")

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()


class Feedback(discord.ui.Modal, title='Feedback'):

    name = discord.ui.TextInput(label='Name', placeholder='Your name here...',)

    feedback = discord.ui.TextInput(
        label='What are your thoughts about my features?',
        style=discord.TextStyle.long,
        placeholder='Type your feedback here...',
        required=False,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message('Thank you for your feedback!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Something went not quite right.', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


parse_env_file(".env")

if MY_GUILD_ID:
    MY_GUILD = discord.Object(int(MY_GUILD_ID))
intents = discord.Intents.all() 
client = ThisClient(command_prefix=".do ", intents=intents)


@client.tree.command()
async def hello(interaction: discord.Interaction):
    "Simply says hello."
    await interaction.response.send_message(f'Salve, {interaction.user.mention}')


@client.tree.command()
async def feedback(interaction: discord.Interaction):
    'Submit feedback'
    await interaction.response.send_modal(Feedback())


@client.tree.command()
@app_commands.checks.has_permissions(administrator=True)
async def shutdown(interaction: discord.Interaction):
    "Gracefully shuts down this bot. (Owner only)"
    #  if for some reason you want to allow other admins to shut down the bot. Remove those lines ---
    if not OWNER_ID:
        await interaction.response.send_message("Seems like Owner ID is missing, contact the Owner!", ephemeral=True)
        return
    if interaction.user.id != int(OWNER_ID):
        await interaction.response.send_message("Not authorised. If you need to shut down the bot - ask the Owner!", ephemeral=True)
        return
    #  ---
    await interaction.response.send_message("Shutting down... Cya!", ephemeral=True)
    await client.close()


@client.command(name='hello')
async def greet(ctx):
    await ctx.send(f'Salut, {ctx.author.mention}!')


async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await client.load_extension(f'cogs.{filename[:-3]}')
            except Exception as error:
                print(f'Failed to load {filename}: {error}')
    print("------")


async def main():

    # logging section
    
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=1024*1024*10,  # (10MB)
        backupCount=5
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if not DISCORD_TOKEN:
        raise RuntimeError("Token is missing!")
    async with client:
        await load()
        await client.start(DISCORD_TOKEN)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nBot stopped manually.")
