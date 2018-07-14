import traceback

import discord
from discord.ext import commands
from . import database

__all__ = ['database']


async def handle_error(ctx, err):
    ignored_errors = (commands.errors.CommandOnCooldown,
                      commands.errors.CheckFailure, commands.errors.CommandNotFound)
    can_send = ctx.channel.permissions_for(ctx.me).send_messages
    if isinstance(err, ignored_errors):
        return
    elif isinstance(err, commands.UserInputError) and can_send:
        await ctx.send("\u274c Bad argument: {}".format(' '.join(err.args)))
    else:
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


def clamp(minimum, value, maximum):
    return min(maximum, max(minimum, value))
