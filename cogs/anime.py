import discord
from discord.ext import commands
import alice
import helper.mediums


import asyncio

class Anime:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self._last_medium = dict() # TODO: Add a time limit or something
        find_command = commands.command()(self.find)
        self.anime.add_command(find_command)

    @commands.group()
    async def anime(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            raise commands.CommandNotFound()
        # TODO: Replace with calling last_medium's anime

    async def find(self, ctx: commands.Context, *, query: str):
        medium_name = ctx.command.parent.name


def setup(bot):
    import importlib
    for v in globals().values():
        try:
            importlib.reload(v)
        except TypeError:
            pass
    bot.add_cog(Anime(bot))
