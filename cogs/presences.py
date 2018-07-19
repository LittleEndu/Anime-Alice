import asyncio
import random

import discord

import alice


class Presences:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self.task = self.bot.loop.create_task(self.presence_updater())

    def __unload(self):
        self.task.cancel()

    async def presence_updater(self):
        # Initial wait
        while not self.bot.is_ready():
            await asyncio.sleep(0)
        # Loop while running
        while self.bot.loop.is_running():
            while not self.bot.is_ready():
                await asyncio.sleep(0)
            game_name = random.choice((
                f'prefix == mention',
            ))
            await self.bot.change_presence(activity=discord.Game(name=game_name))
