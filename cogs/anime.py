import asyncio

from discord.ext import commands

import alice
import helper.mediums


class Anime:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self._last_medium = dict()  # TODO: Add a time limit or something
        find_command = commands.command(aliases=['?', 'search'])(self.find)
        lucky_command = commands.command(aliases=['!', 'luckysearch'])(self.lucky)
        for g in [self.anime]:
            for s in [find_command, lucky_command]:
                g.add_command(s)

    async def last_medium_caller(self, ctx: commands.Context, parent_name: str, lucky=False):
        medium = self._last_medium.get(ctx.author.id)
        if not medium:
            await ctx.send("You haven't used last medium yet")
            return
        func = getattr(medium, parent_name)
        try:
            new_medium = await func(lucky=lucky)
        except asyncio.TimeoutError:
            return
        if new_medium is NotImplemented:
            await ctx.send("I'm sorry. I can't do that yet.")
        elif new_medium is None:
            await ctx.send('No results...')
        else:
            embed = new_medium.to_embed()
            await ctx.send(embed=embed)
            self._last_medium[ctx.author.id] = new_medium

    @commands.group(aliases=['hentai'])
    async def anime(self, ctx: commands.Context):
        if ctx.invoked_with == 'hentai' and not ctx.channel.nsfw:
            await ctx.send("Can't search hentai in here")
        if ctx.invoked_subcommand is None:
            await self.last_medium_caller(ctx, 'anime', False)
            return

    async def lucky(self, ctx: commands.Context, *, query: str = None):
        if query is None:
            await self.last_medium_caller(ctx, ctx.command.parent.name, True)
            return
        await self.find_helper(ctx, query, True)

    async def find(self, ctx: commands.Context, *, query: str = None):
        if query is None:
            await self.last_medium_caller(ctx, ctx.command.parent.name, False)
            return
        await self.find_helper(ctx, query, False)

    async def find_helper(self, ctx, query, lucky):
        medium_name = ctx.command.parent.name
        cls = getattr(helper.mediums, medium_name.capitalize())
        assert issubclass(cls, helper.mediums.Medium)
        await ctx.trigger_typing()
        try:
            medium = await cls.via_search(ctx, query, adult=ctx.channel.nsfw, lucky=lucky)
        except asyncio.TimeoutError:
            return
        if medium is NotImplemented:
            await ctx.send("I'm sorry. I can't do that yet.")
        elif medium is None:
            await ctx.send('No results...')
        else:
            embed = medium.to_embed()
            await ctx.send(embed=embed)
            self._last_medium[ctx.author.id] = medium


def setup(bot):
    import importlib
    for v in globals().values():
        try:
            importlib.reload(v)
        except TypeError:
            pass
    bot.add_cog(Anime(bot))
