import asyncio
import random

import async_timeout
import discord
from discord.ext import commands

import alice


class Presences:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self.task = self.bot.loop.create_task(self.presence_updater())
        self.status = discord.Status.online
        self.emojis = dict()

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
    @commands.bot_has_permissions(add_reactions=True)
    @commands.is_owner()
    async def setstatus(self, ctx, emoji: str = None):
        if not self.emojis:
            # await bot.wait_for_ready() except bot can't respond to commands without being ready...
            my_guild = discord.utils.get(self.bot.guilds, owner=self.bot.user)
            self.emojis = [i for i in my_guild.emojis if hasattr(discord.Status, i.name)]
        if emoji is None:
            async def reaction_waiter(msg: discord.Message, choice_fut: asyncio.Future):
                def reaction_check(r: discord.Reaction, u: discord.User):
                    return all([
                        u.id == ctx.author.id,
                        r.message.id == msg.id,
                        r.emoji in self.emojis])

                reaction, user = await ctx.bot.wait_for('reaction_add', check=reaction_check)
                try:
                    choice_fut.set_result(reaction.emoji)
                except asyncio.InvalidStateError:
                    return

            msg = await ctx.send('Please choose')
            fut = asyncio.Future()
            task = self.bot.loop.create_task(reaction_waiter(msg, fut))
            for i in self.emojis:
                if fut.done():
                    break
                await msg.add_reaction(i)
            message_exists = True
            try:
                async with async_timeout.timeout(60):
                    while not fut.done():
                        await asyncio.sleep(0)
            except asyncio.TimeoutError:
                await msg.delete()
                message_exists = False
                raise
            else:
                emoji = fut.result().name
            finally:
                task.cancel()
                if message_exists:
                    await msg.delete()

        emoji = ''.join([i for i in emoji if i.isalpha()])
        if emoji == 'offline':
            emoji = 'invisible'
        status = discord.Status[emoji]
        current_activity = ctx.me.activity.name
        await self.bot.change_presence(activity=discord.Game(name=current_activity), status=status)
        if not await self.bot.helper.react_or_false(ctx):
            await ctx.send(f'Set my status to {status}')


def setup(bot):
    bot.add_cog(Presences(bot))
