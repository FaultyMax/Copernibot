

import json
import os
import logging
from datetime import datetime, timezone
from typing import List

import discord
from discord import app_commands
from discord.ext import commands, tasks

RULES_FILE = "cleaners.json"
LOOP_TIME = 30
SECONDS_IN_HOUR = 3600

log = logging.getLogger(__name__)

'''TO DO: 

Think about using discord.purge() instead of manually deleting every line

'''


def load_rules():
    if not os.path.exists(RULES_FILE):
        return []
    with open(RULES_FILE, "r") as f:
        return json.load(f)


def save_rules(rules) -> None:
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=4)


class Cleaner(commands.Cog):
    """Cleaner for text channels."""

    def __init__(self, bot):
        self.bot = bot
        self.rules = load_rules()
        self.clean_loop.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} loaded!")

    def cog_unload(self):
        self.clean_loop.cancel()

    @tasks.loop(minutes=LOOP_TIME)
    async def clean_loop(self):

        now = datetime.now(timezone.utc)

        print(f"Trying to clean! Time: {str(datetime.now().time())}")

        for rule in self.rules:

            channel = self.bot.get_channel(rule["channel_id"])
            if not channel:
                continue

            limit = rule["limit_in_seconds"]
            user_id = rule["user_id"]  # None -> any user
            delete_pinned = rule["delete_pinned"]

            try:
                async for message in channel.history(limit=256):

                    age = (now - message.created_at).total_seconds()
                    author_match = (message.author.id == user_id) or (user_id is None)  # because None means any user

                    if age > limit and author_match:

                        if message.pinned and not delete_pinned:
                            continue

                        try:
                            await message.delete()
                        except discord.Forbidden:
                            log.error(f"I'm missing permissions! #{channel.name}", exc_info=True)
                        except discord.HTTPException as error:
                            log.error(f"Failed to delete message: {error}", exc_info=True)
            except discord.Forbidden:
                log.error(f"I can't read history in #{channel.name}!", exc_info=True)

    @clean_loop.before_loop
    async def before_clean(self):
        await self.bot.wait_until_ready()

    # Implementing slash command

    cleaner_group = app_commands.Group(name="cleaner", description="Manage channel cleaning")

    @cleaner_group.command(name="add", description="Add a cleaner to a channel")
    @app_commands.describe(
        channel="The channel to clean",
        hour="Delete messages older than this many hours",
        user="Delete messages from this user (empty=everyone)",
        delete_pinned="Choose whether you want to delete pinned messages or not"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def cleaner_add(
        self, interaction: discord.Interaction,
        channel: discord.TextChannel,
        hour: int,
        user: discord.Member | None = None,
        delete_pinned: bool = False
    ):

        rule = {
            "channel_id": channel.id,
            "user_id": user.id if user else None,
            "limit_in_seconds": hour * SECONDS_IN_HOUR,
            "delete_pinned": delete_pinned
        }

        user_str = user.mention if user else "everyone"

        for existing in self.rules:
            if existing["channel_id"] == rule["channel_id"] and existing["user_id"] == rule["user_id"]:
                #  Duplicate found, override current rules

                existing["limit_in_seconds"] = rule["limit_in_seconds"]
                existing["delete_pinned"] = rule["delete_pinned"]
                save_rules(self.rules)

                await interaction.response.send_message(
                    f"Cleaner overridden: deleting messages older than {hour} hours in {channel.name} from {user_str}. (DELETING PINNED: {delete_pinned})",
                    ephemeral=True
                )
                return 

        self.rules.append(rule)
        save_rules(self.rules)

        await interaction.response.send_message(
            f"Cleaner added: deleting messages older than {hour} hours in {channel.name} from {user_str}. (DELETING PINNED: {delete_pinned})",
            ephemeral=True
        )

    @cleaner_group.command(name="remove", description="Remove a cleaner")
    @app_commands.describe(
        channel="the channel in which the cleaner will be removed",
        user="The user of this specific cleaner to remove (empty=everyone)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def cleaner_remove(self, interaction: discord.Interaction, channel: discord.TextChannel, user: discord.Member | None = None):

        user_id = user.id if user else None
        before = len(self.rules)

        '''
        if user is not None:
            if user == 1:
                print("Chosen, remove every cleaner")
                return
        '''

        new_rules = [r for r in self.rules if not (r["channel_id"] == channel.id and r["user_id"] == user_id)]

        if len(new_rules) == before:
            await interaction.response.send_message("No matching cleaner found.", ephemeral=True)
            return

        save_rules(new_rules)
        self.rules = new_rules

        user_str = user.name if user else "everyone"
        await interaction.response.send_message(
            f"Cleaner removed: No longer removing messages in {channel.name} from {user_str}.",
            ephemeral=True
        )

    @cleaner_group.command(name="list", description="List all running cleaners")
    @app_commands.checks.has_permissions(administrator=True)
    async def cleaner_list(self, interaction: discord.Interaction):

        if not self.rules:
            await interaction.response.send_message(
                "No cleaners set up yet.",
                ephemeral=True
            )
            return

        lines: List[str] = []
        for c in self.rules:

            channel = self.bot.get_channel(c["channel_id"])
            channel_str = channel.name if channel else f"unknown channel? ID: {c["channel_id"]}"
            user_str = f"{c["user_id"]}" if c["user_id"] else "everyone"
            hour = c["limit_in_seconds"] // 3600
            delete_pinned = c["delete_pinned"]

            lines.append(f"--- {channel_str} --- Delete messages from <@{user_str}> older than this many hours: {hour} --- deleting pinned? {delete_pinned} ---")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Cleaner(bot))
