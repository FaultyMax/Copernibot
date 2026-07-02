

import json
import os
import logging
import aiohttp
import aiofiles  # type: ignore[import-untyped]
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

BACKUP_BASE = "backup"

log = logging.getLogger(__name__)


async def download_attachment(session: aiohttp.ClientSession, url: str, dest_path: str):

    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(dest_path, "wb") as file:
                    await file.write(await resp.read())
                return True
    except Exception as error:
        log.error(f"Failed to download {url}: {error}", exc_info=True)
    return False


class Backup(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} loaded!")

    @app_commands.command(name="backup", description="Backup text channels to the bot's catalogue")
    @app_commands.describe(channel="Channel to backup from, leave it empty to backup all the text channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):

        await interaction.response.defer(ephemeral=True)

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = os.path.join(BACKUP_BASE, f"backup_{now}")
        os.makedirs(backup_dir, exist_ok=True)

        target_channels = [channel] if channel else interaction.guild.text_channels  # type: ignore[union-attr]

        async with aiohttp.ClientSession() as session:
            for ch in target_channels:

                channel_dir = os.path.join(backup_dir, ch.name)
                attachments_dir = os.path.join(channel_dir, "attachments")
                os.makedirs(attachments_dir, exist_ok=True)

                messages = []

                try:
                    async for message in ch.history(limit=None, oldest_first=True):

                        saved_attachments = []

                        for attachment in message.attachments:

                            filename = f"{message.id}_{attachment.filename}"
                            dest = os.path.join(attachments_dir, filename)
                            success = await download_attachment(session, attachment.url, dest)

                            saved_attachments.append({
                                "filename": attachment.filename,
                                "url": attachment.url,
                                "saved_locally": filename if success else None,
                                "size_bytes": attachment.size,
                                "content_type": attachment.content_type
                            })

                        messages.append({
                            "id": message.id,
                            "author": str(message.author),
                            "author_id": message.author.id,
                            "content": message.content,
                            "pinned": message.pinned,
                            "attachments": saved_attachments,
                            "embeds": [e.to_dict() for e in message.embeds],
                            "reply_to": message.reference.message_id if message.reference else None
                        })

                except discord.Forbidden:
                    log.warning(f"Can't access #{ch.name}! I have to skip it.")
                    continue
                except Exception as error:
                    log.error(f"Error while backing up #{ch.name}: {error}", exc_info=True)
                    continue

                json_path = os.path.join(channel_dir, f"{ch.name}.json")
                async with aiofiles.open(json_path, "w", encoding="utf-8") as file:
                    await file.write(json.dumps(messages, indent=4, ensure_ascii=False))

                log.info(f"Backed up #{ch.name} - {len(messages)} messages.")

            await interaction.followup.send(f"Backup succesful. Saved to '{backup_dir}'.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Backup(bot))
