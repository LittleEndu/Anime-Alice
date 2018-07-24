import asyncio
import logging
import os
import random
import concurrent.futures
from logging.handlers import RotatingFileHandler

import async_timeout
import dbl
import discord
from discord.ext import commands

import alice


class Presences:
    def __init__(self, bot: alice.Alice):
        self.bot = bot
        gh = RotatingFileHandler("logs/guilds.log", maxBytes=5000000, backupCount=1, encoding='UTF-8')
        gh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s'))
        gh.setLevel(1)
        self.guilds_logger = logging.getLogger('alice.guilds')
        self.guilds_logger.addHandler(self.bot.trace_handler)
        self.guilds_logger.addHandler(gh)

        self.task = self.bot.loop.create_task(self.presence_updater())
        if not os.path.isfile('status'):
            self.status = bot.guilds[0].me.status
        else:
            with open('status') as in_file:
                self.status = discord.Status[in_file.read()]
        self.dbl_client = None
        self.dbl_logger = logging.getLogger('alice.dbl')
        if self.bot.config.get('dbl_token'):
            self.dbl_client = dbl.Client(self.bot, self.bot.config.get('dbl_token'))
        self.emojis = list()

    def __unload(self):
        self.task.cancel()

    async def on_guild_join(self, guild: discord.Guild):
        self.guilds_logger.debug(f"Joined new guild:\n"
                                 f"name={guild.name}\n"
                                 f"id={guild.id}\n"
                                 f"channels={len(guild.channels)}"
                                 f"bot/members={sum(i.bot for i in guild.members)/len(guild.members)}\n"
                                 f"total members={len(guild.members)}")
        if any((sum(i.bot for i in guild.members) / len(guild.members) > 0.8,
                len(guild.members) - sum(i.bot for i in guild.members) < 3)):
            self.guilds_logger.info(f'Joined guild {guild.id} seems to be full of bots')

    async def on_guild_remove(self, guild: discord.Guild):
        self.guilds_logger.debug(f"Guild {guild.id} was removed")

    async def presence_updater(self):
        try:
            # Initial wait
            await self.bot.wait_until_ready()
            if self.dbl_client:
                while not self.dbl_client.bot_id:
                    await asyncio.sleep(0)
            # Loop while running
            while self.bot.loop.is_running():
                try:
                    while not self.bot.is_ready():
                        await asyncio.sleep(0)
                    game_name = random.choice((
                        f'prefix == mention',
                    ))
                    await self.bot.change_presence(activity=discord.Game(name=game_name), status=self.status)
                    if self.dbl_client:
                        try:
                            await self.dbl_client.post_server_count()
                        except Exception as e:
                            self.dbl_logger.error(f"Failed to post guild count to dbl: {repr(e)}")
                            self.dbl_logger.info(
                                f"Guild count would have been {self.dbl_client.guild_count()} "
                                f"for id:{self.dbl_client.bot_id}"
                            )
                    await asyncio.sleep(600)
                except Exception as err:
                    if isinstance(err, concurrent.futures.CancelledError):
                        raise
                    self.bot.logger.error(f"Error while updating presence: {repr(err)}")
        except concurrent.futures.CancelledError:
            pass

    @commands.command(hidden=True)
    @commands.bot_has_permissions(add_reactions=True, external_emojis=True)
    @commands.is_owner()
    async def setstatus(self, ctx, emoji: str = None):
        """Sets the bots status"""
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
        reaction = discord.utils.get(self.emojis, name=emoji)
        await self.bot.change_presence(activity=discord.Game(name=current_activity), status=status)
        if not await self.bot.helper.react_or_false(ctx, ('\u2705', reaction)):
            await ctx.send(f'Set my status to {status}')
        with open('status', 'w') as out_file:
            out_file.write(status.name)


def setup(bot):
    bot.add_cog(Presences(bot))
