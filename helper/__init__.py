import traceback

import asyncio

import async_timeout
import discord
from discord.ext import commands

from . import database, mediums

__all__ = ['database', 'mediums']


async def handle_error(ctx, err):
    can_send = ctx.channel.permissions_for(ctx.me).send_messages
    if not can_send:
        await react_or_false(ctx, ("\U0001f507",))
    if isinstance(err, commands.errors.CommandOnCooldown):
        if not await react_or_false(ctx, ("\u23f0",)) and can_send:
            await ctx.send("\u23f0 " + str(err))
        return
    if isinstance(err, commands.UserInputError) and can_send:
        await ctx.send("\u274c Bad argument: {}".format(' '.join(err.args)))
    elif isinstance(err, commands.errors.CheckFailure) and can_send:
        if ctx.command.hidden:
            return await react_or_false(ctx, ("\u2753",))
        await ctx.send("\u274c Check failure. " + str(err))
    elif isinstance(err, commands.errors.CommandNotFound):
        await react_or_false(ctx, ("\u2753",))
    else:
        content = "\u274c Error occurred while handling the command."
        if isinstance(err, commands.errors.CommandInvokeError):
            if isinstance(err.original, discord.errors.HTTPException):
                content = None
        if content:
            await ctx.send(content)
        if ctx.command.name == 'debug':
            return
        ctx.bot.logger.error("{}.{}".format(err.__class__.__module__, err.__class__.__name__))
        ctx.bot.logger.trace("".join(traceback.format_exception(type(err), err, err.__traceback__)))
        ctx.bot.logger.trace("".join(traceback.format_exception(type(err), err.__cause__, err.__cause__.__traceback__)))


async def react_or_false(ctx, reactions=("\u2705",)):
    if ctx.channel.permissions_for(ctx.me).add_reactions:
        for r in reactions:
            try:
                await ctx.message.add_reaction(r)
            except:
                continue
        return True
    return False


def clamp(minimum, value, maximum):
    return min(maximum, max(minimum, value))


def number_to_reaction(number: int):
    return f"{number}\u20E3"


def reaction_to_number(reaction: str):
    try:
        return int(reaction[0])
    except:
        return None


class Asker:
    def __init__(self, ctx: commands.Context, *args, choices: tuple = tuple()):
        self.ctx = ctx
        self.choices = []
        for choice in args + choices:
            if hasattr(choice, 'discord_str'):
                self.choices.append(choice.discord_str())
            else:
                self.choices.append(str(choice))
        if len(self.choices) > 9:
            raise ValueError("Amount of choices can't exceed 9")
        self.chosen = None

    def get_choice(self):
        return self.chosen

    def __await__(self):
        if self.chosen:
            raise asyncio.InvalidStateError
        return self.make_choice().__await__()

    async def make_choice(self):
        if self.chosen:
            raise asyncio.InvalidStateError

        async def reaction_waiter(msg: discord.Message, choice_fut: asyncio.Future):
            def reaction_check(r: discord.Reaction, u: discord.User):
                return all([
                    u.id == self.ctx.author.id,
                    r.message.id == msg.id,
                    0 < reaction_to_number(r.emoji) <= len(self.choices)])

            reaction, user = await self.ctx.bot.wait_for('reaction_add', check=reaction_check)
            try:
                choice_fut.set_result(reaction_to_number(reaction.emoji))
            except asyncio.InvalidStateError:
                return

        async def message_waiter(choice_fut: asyncio.Future):
            def message_check(message: discord.Message):
                try:
                    number = int(message.content)
                except:
                    return False
                else:
                    return message.author.id == self.ctx.author.id and 0 < number <= len(self.choices)

            msg = await self.ctx.bot.wait_for('message', check=message_check)
            try:
                choice_fut.set_result(int(msg.content))
            except asyncio.InvalidStateError:
                return

        emb = discord.Embed(
            title="Please choose",
            description="\n".join([f"**{i+1}**: {self.choices[i]}" for i in range(len(self.choices))]).strip()
        )
        asker = await self.ctx.send(embed=emb)
        fut = asyncio.Future()
        reaction_task = self.ctx.bot.loop.create_task(reaction_waiter(asker, fut))
        message_task = self.ctx.bot.loop.create_task(message_waiter(fut))
        if self.ctx.channel.permissions_for(self.ctx.me).add_reactions:
            for em in map(number_to_reaction, range(1, len(self.choices) + 1)):
                if fut.done():
                    break
                await asker.add_reaction(em)
        message_exists = True
        try:
            async with async_timeout.timeout(60):
                while not fut.done():
                    await asyncio.sleep(0)
        except asyncio.TimeoutError:
            await asker.delete()
            message_exists = False
        finally:
            reaction_task.cancel()
            message_task.cancel()
            if not message_exists:
                return
            await asker.delete()
        self.chosen = fut.result() - 1
        return self.chosen


class AppendOrSend:
    def __init__(self, channel: discord.abc.Messageable):
        self.data = ""
        self.channel = channel

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.flush()

    async def append(self, arg: str):
        if not isinstance(arg, str):
            arg = str(arg)
        if len(self.data) + len(arg) > 2000:
            await self.channel.send(self.data)
            self.data = arg
        else:
            self.data += arg

    async def flush(self):
        await self.channel.send(self.data)
        self.data = ""
