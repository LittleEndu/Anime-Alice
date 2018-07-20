import asyncio
import asyncpg
import discord
from discord.ext import commands

import alice
import helper


class Prefixes:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self.bot.loop.create_task(self.db_init())

    async def db_init(self):
        await self.bot.database.wait_for_start()
        await self.bot.database.create_prefixes_table()

    @commands.command(aliases=['prefix'])
    @commands.bot_has_permissions(embed_links=True)
    async def prefixes(self, ctx):
        """Lists prefixes"""
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("There's no need for any prefix in DMs")
            return
        prefixes = await self.bot.get_prefix(ctx.message)
        mentions = commands.bot.when_mentioned(ctx.bot, ctx.message)
        prefixes = [i for i in prefixes if i not in mentions]
        emb = discord.Embed()
        val = ""
        counter = 0
        for p in prefixes:
            counter += 1
            if p.strip() != p:
                val += '(No <>) **{}.** <{}>\n'.format(counter, p)
            else:
                val += "**{}.** {}\n".format(counter, p)
        if not val:
            val = "No prefixes"
        emb.add_field(name="Prefixes for {} are".format(
            "PMs" if isinstance(ctx.channel, discord.DMChannel) else "this server"),
            value=val.strip())
        emb.set_footer(text="You can also just mention me")
        await ctx.send(embed=emb)

    @commands.command(aliases=['addprefix'])
    async def setprefix(self, ctx: commands.Context, *, prefix: str):
        """Sets prefix for the bot in this server"""
        if not (ctx.author.guild_permissions.administrator or self.bot.is_owner(ctx.author)):
            raise commands.CheckFailure("You can't change the prefix")
        if await self.bot.database.count_prefixes(ctx.guild) > 4:
            await ctx.send("You already have enough prefixes")
            return
        try:
            await self.bot.database.add_prefix(ctx.guild, prefix)
        except asyncpg.UniqueViolationError:
            await ctx.send("That prefix already exists")
            return
        if not await helper.react_or_false(ctx):
            await ctx.send("Successfully set the prefix.")

    @commands.command(aliases=['deleteprefix'])
    async def removeprefix(self, ctx, prefix: str):
        """Removes prefix for the bot from this server"""
        if not (ctx.author.guild_permissions.administrator or self.bot.is_owner(ctx.author)):
            raise commands.CheckFailure("You can't change the prefix")
        await self.bot.database.remove_prefix(ctx.guild, prefix)
        if not await helper.react_or_false(ctx, ("\U0001f6ae", "\u2705")):
            await ctx.send("Prefix successfully deleted.")




def setup(bot):
    import importlib
    for v in globals().values():
        try:
            importlib.reload(v)
        except TypeError:
            pass
    bot.add_cog(Prefixes(bot))
