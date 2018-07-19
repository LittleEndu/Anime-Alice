import discord
from discord.ext import commands
import alice
import helper.mediums

import asyncio


class Anime:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self._last_medium = dict()  # TODO: Add a time limit or something
        find_command = commands.command(aliases=['?', 'search'])(self.find)
        self.anime.add_command(find_command)

    @commands.group()
    async def anime(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            raise commands.CommandNotFound()
        # TODO: Replace with calling last_medium's anime

    async def find(self, ctx: commands.Context, *, query: str):
        medium_name = ctx.command.parent.name
        cls = getattr(helper.mediums, medium_name.capitalize())
        assert issubclass(cls, helper.mediums.Medium)
        await ctx.trigger_typing()
        medium = await cls.via_search(ctx, query)
        if medium is NotImplemented:
            await ctx.send("I'm sorry. I can't do that yet.")
        elif medium is None:
            await ctx.send('No results...')
        else:
            await ctx.send(embed=medium.to_embed())




def setup(bot):
    import importlib
    for v in globals().values():
        try:
            importlib.reload(v)
        except TypeError:
            pass
    bot.add_cog(Anime(bot))
