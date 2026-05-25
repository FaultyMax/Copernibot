
import discord

DISCORD_TOKEN = None
APP_ID = None
PUBLIC_KEY = None


class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user} :O")

    async def on_message(self, message):
        print(f"Message from {message.author}: {message.content}")


def parse_file(path):

    with open(path, "r") as file:

        print(f"parsing {path}...")

        for line in file:

            line = line.strip()
            if not line:
                continue

            key, value = line.split("=", 1)
            value = value.strip("<>")

            globals()[key] = value

            print(f"\tValue: <{value}> added to var: {key}")

    return True


intents = discord.Intents.default()
intents.message_content = True
parse_file(".env")

client = MyClient(intents=intents)

if DISCORD_TOKEN is not None:
    client.run(DISCORD_TOKEN)
