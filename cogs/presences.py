import asyncio
import random

import discord
from discord.ext import commands

import alice


class Presences:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self.task = self.bot.loop.create_task(self.presence_updater())
        self.status = discord.Status.online
        self.emotes = dict()

    def __unload(self):
        self.task.cancel()

    async def presence_updater(self):
        try:
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
                await self.bot.change_presence(activity=discord.Game(name=game_name), status=self.status)
                await asyncio.sleep(600)
            # TODO: add dbply report here
        except asyncio.CancelledError:
            pass

    @commands.command(hidden=True)
    @commands.is_owner()
    async def setstatus(self, ctx, emoji: str = None):
        if not self.emotes:
            # await bot.wait_for_ready() except bot can't respond to commands without being ready...
            my_guild = discord.utils.get(self.bot.guilds, owner=self.bot.user)
            self.emotes = [i for i in my_guild.emojis if hasattr(discord.Status, i.name)]
        if emoji is None:
            try:
                index = await self.bot.helper.Asker(ctx, *[i.name for i in self.emotes])
            except asyncio.TimeoutError:
                return
            emoji = self.emotes[index]
        emoji = ''.join([i for i in emoji if i.isalpha()])
        if emoji == 'offline':
            emoji = 'invisible'
        status = discord.Status[emoji]
        current_activity = await ctx.me.activity.name
        await self.bot.change_presence(activity=discord.Game(name=current_activity), status=status)
        if not await self.bot.helper.react_or_false(ctx):
            await ctx.send(f'Set my status to {status}')


def setup(bot):
    bot.add_cog(Presences(bot))
