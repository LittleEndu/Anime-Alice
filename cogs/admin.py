import os

import asyncio
from discord.ext import commands

import alice


class Admin:
    def __init__(self, bot:alice.Alice):
        self.bot = bot

    @commands.command(aliases=['git'])
    @commands.is_owner()
    async def gitreload(self, ctx: commands.Context):
        fut = self.bot.loop.run_in_executor(self.bot.executor, os.system, 'git pull')
        while not fut.done():
            await asyncio.sleep(0)
        if not fut.result() == 0:
            await ctx.send('There was an error pulling from git')
            return
        await ctx.send('Successfully pulled from git')
        reload = self.bot.get_command('reload')
        await reload.callback(self.bot, ctx)

def setup(bot):
    bot.add_cog(Admin(bot))