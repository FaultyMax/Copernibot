import logging
import traceback

import discord
from discord import app_commands

DISCORD_TOKEN = None
APP_ID = None
PUBLIC_KEY = None
MY_GUILD_ID = None  # temporary

log_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')


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


class MyClient(discord.Client):
    '''Represents a client connection that connects to Discord. This class is used to interact with the Discord WebSocket and API.'''

    user: discord.ClientUser  # so the type checker won't complain

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f"Logged on as {self.user}")
        print("------")

    async def on_message(self, message):
        print(f"Message from {message.author}: {message.content}")

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


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


intents = discord.Intents.default() 
intents.message_content = True
intents.members = True


parse_env_file(".env")

if MY_GUILD_ID:
    MY_GUILD = discord.Object(int(MY_GUILD_ID))
client = MyClient(intents=intents)


@client.tree.command()
async def hello(interaction: discord.Interaction):
    "Simply says hello."
    await interaction.response.send_message(f'Salve, {interaction.user.mention}')


@client.tree.command()
async def feedback(interaction: discord.Interaction):
    'Submit feedbak'
    await interaction.response.send_modal(Feedback())

help(MyClient)

if DISCORD_TOKEN is not None:
    client.run(DISCORD_TOKEN)
