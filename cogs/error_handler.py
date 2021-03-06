import collections
import logging
import traceback
from abc import ABCMeta, abstractmethod
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

# noinspection PyUnreachableCode
if False:
    import alice


class UnhandledError(Exception):
    pass


class DefaultHandler(metaclass=ABCMeta):
    def __init__(self, priority=None):
        self.priority = -1
        if priority is not None:
            self.priority = priority

    @abstractmethod
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        raise UnhandledError

    def __str__(self):
        return f"<{self.__class__.__name__}>"


class InvokeHandler(DefaultHandler):
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        ctx.bot: 'alice.Alice' = ctx.bot
        if isinstance(err, commands.CommandInvokeError):
            if ctx.command.name == 'debug':
                return
            ctx.bot.logger.error(
                "CommandInvokeError {}.{}".format(err.original.__class__.__module__, err.original.__class__.__name__))
            ctx.bot.logger.debug("".join(traceback.format_exception(type(err), err, err.__traceback__)))
            ctx.bot.logger.debug(
                "".join(traceback.format_exception(type(err), err.__cause__, err.__cause__.__traceback__))
            )
            content = "\u274c Error occurred while handling the command."
            if content:
                await ctx.send(content)
        else:
            await super().handle(ctx, err)


class NotFoundHandler(DefaultHandler):
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, commands.errors.CommandNotFound):
            await ctx.bot.helper.react_or_false(ctx, ("\u2753",))
            try:
                logger = ctx.bot.commands_logger
            except AttributeError:
                logger = logging.getLogger('alice.commands')
                ch = RotatingFileHandler("logs/commands.log", maxBytes=5000000, backupCount=1, encoding='UTF-8')
                ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s'))
                ch.setLevel(1)
                logger.handlers = []  # Shouldn't matter but still
                logger.addHandler(ctx.bot.alice_handler)
                logger.addHandler(ch)
                ctx.bot.commands_logger = logger
            logger.info(f'Unknown command: {ctx.invoked_with}')
        else:
            await super().handle(ctx, err)


class CheckFailureHandler(DefaultHandler):
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, commands.errors.CheckFailure):
            if any(i.__qualname__.startswith('is_owner') for i in ctx.command.checks):
                return await ctx.bot.helper.react_or_false(ctx, ("\u2753",))
            await ctx.send("\u274c Check failure. " + str(err))
        else:
            await super().handle(ctx, err)


class BadInputHandler(DefaultHandler):
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, commands.UserInputError):
            await ctx.send("\u274c Bad argument: {}".format(' '.join(err.args)))
        else:
            await super().handle(ctx, err)


class ConversionHandler(DefaultHandler):
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, commands.errors.ConversionError):
            await ctx.send("\u274c Bad argument: Failed to use converter. "
                           "You shouldn't see this error, please report it")
        else:
            await super().handle(ctx, err)


class CooldownHandler(DefaultHandler):
    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, commands.CommandOnCooldown):
            if not await ctx.bot.helper.react_or_false(ctx, ("\u23f0",)):
                await ctx.send("\u23f0 " + str(err))
        else:
            await super().handle(ctx, err)


class CanNotSendHandler(DefaultHandler):
    def __init__(self, priority=float('inf')):
        super().__init__(priority)  # I want this to trigger no matter what

    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if not ctx.channel.permissions_for(ctx.me).send_messages:
            await ctx.bot.helper.react_or_false(ctx, ("\U0001f507",))
        else:
            await super().handle(ctx, err)


class HandlersManager:
    def __init__(self, *args, handlers: collections.Iterable = tuple()):
        self.handlers = list(args + tuple(i for i in handlers))

    def add_handler(self, handler: DefaultHandler):
        if not isinstance(handler, DefaultHandler):
            raise TypeError
        self.handlers.append(handler)

    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        self.handlers.sort(key=lambda a: a.priority, reverse=True)
        for handler in self.handlers:
            if not isinstance(handler, DefaultHandler):
                ctx.bot.logger.debug("Error handler tried using something that isn't DefaultHandler")
                continue
            try:
                await handler.handle(ctx, err)
                return
            except UnhandledError:
                continue
            except Exception as e:
                ctx.bot.logger.debug(f"{handler} couldn't handle {err.__class__.__name__} error correctly")
                ctx.bot.logger.debug(f"It raised: {repr(e)}")
                continue
        ctx.bot.logger.debug(f'Unhandled error of type {type(err)}')
        try:
            await ctx.message.add_reaction('\u26a0')
        except discord.Forbidden:
            pass


class ErrorCog:
    def __init__(self, bot: 'alice.Alice'):
        self.bot = bot
        self.error_handler = HandlersManager()
        handlers = [
            InvokeHandler,
            NotFoundHandler,
            CheckFailureHandler,
            BadInputHandler,
            ConversionHandler,
            CooldownHandler
        ]
        for priority, cls in enumerate(handlers):
            self.error_handler.add_handler(cls(priority=priority))
        self.error_handler.add_handler(CanNotSendHandler())

    def add_handler(self, handler: DefaultHandler):
        self.error_handler.add_handler(handler)

    async def on_command_error(self, ctx, err):
        if hasattr(ctx.command, "on_error"):
            return
        await self.error_handler.handle(ctx, err)


def setup(bot):
    bot.add_cog(ErrorCog(bot))
