import asyncio
import collections
import logging
import math
import traceback

import async_timeout
import discord
from discord.ext import commands
from logging.handlers import RotatingFileHandler

if False:
    import alice


class Helper:
    # region discord stuff
    @staticmethod
    async def handle_error(ctx: commands.Context, err):
        can_send = ctx.channel.permissions_for(ctx.me).send_messages
        if not can_send:
            await Helper.react_or_false(ctx, ("\U0001f507",))
        if isinstance(err, commands.errors.CommandOnCooldown):
            if not await Helper.react_or_false(ctx, ("\u23f0",)) and can_send:
                await ctx.send("\u23f0 " + str(err))
            return
        if isinstance(err, commands.UserInputError) and can_send:
            await ctx.send("\u274c Bad argument: {}".format(' '.join(err.args)))
        elif isinstance(err, commands.errors.CheckFailure) and can_send:
            if ctx.command.hidden:
                return await Helper.react_or_false(ctx, ("\u2753",))
            await ctx.send("\u274c Check failure. " + str(err))
        elif isinstance(err, commands.errors.CommandNotFound):
            await Helper.react_or_false(ctx, ("\u2753",))
            try:
                logger = ctx.bot.commands_logger
            except AttributeError:
                logger = logging.getLogger('alice.commands')
                ch = RotatingFileHandler("logs/commands.log", maxBytes=5000000, backupCount=1, encoding='UTF-8')
                ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s [%(name)s] %(message)s'))
                ch.setLevel(1)
                logger.addHandler(ctx.bot.alice_handler)
                logger.addHandler(ch)
                ctx.bot.commands_logger = logger
            logger.info(f'Unknown command: {ctx.invoked_with}')
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
            ctx.bot.logger.debug("".join(traceback.format_exception(type(err), err, err.__traceback__)))
            ctx.bot.logger.debug(
                "".join(traceback.format_exception(type(err), err.__cause__, err.__cause__.__traceback__)))

    @staticmethod
    async def react_or_false(ctx, reactions: collections.Iterable = ("\u2705",)):
        if ctx.channel.permissions_for(ctx.me).add_reactions:
            aa = True
            for r in reactions:
                try:
                    await ctx.message.add_reaction(r)
                except:
                    aa = False
                    continue
            return aa
        return False

    @staticmethod
    def number_to_reaction(number: int):
        if not isinstance(number, int):
            return "\u26a0"
        if number == 10:
            return '\U0001f51f'
        if 9 < number < 0:
            return "\u26a0"
        return f"{number}\u20E3"

    @staticmethod
    def reaction_to_number(reaction: str):
        try:
            return int(reaction[0])
        except:
            return -1

    @staticmethod
    def safety_escape_monospace(string: str):
        safe = str(string).replace('`', '\u02cb').replace('*', '\u2217')
        return f"``{safe}``"

    @staticmethod
    def saftey_escape_regular(string: str):
        return str(string).replace('`', '\u02cb').replace('*', '\u2217')

    # endregion

    # region general stuff
    @staticmethod
    def clamp(minimum, value, maximum):
        return min(maximum, max(minimum, value))

    @staticmethod
    def ci_score(ratings: list):
        pos = sum([ratings[i] * i / (len(ratings) - 1) for i in range(1, len(ratings))])
        n = sum([i for i in ratings])
        return Helper.ci(pos, n) * 10

    @staticmethod
    def ci(pos, n):
        z = 1.98
        phat = 1.0 * pos / n

        return (phat + z * z / (2 * n) - z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)) / (1 + z * z / n)

    # endregion

    # region classes

    class AdditionalInfo:
        def __init__(self, ctx: commands.Context, *args, questions: tuple = tuple(), ):
            self.ctx = ctx
            self.questions = []
            for i in args + questions:
                self.questions.append(str(i))

        def __await__(self):
            return self.ask_for_more_info().__await__()

        async def ask_for_more_info(self):
            async def message_waiter(answer_fut: asyncio.Future):
                def message_check(message: discord.Message):
                    return message.author.id == self.ctx.author.id and message.channel.id == self.ctx.channel.id

                msg = await self.ctx.bot.wait_for('message', check=message_check)
                answer_fut.set_result(msg.content)

            answers = []
            for question in self.questions:
                await self.ctx.send(question)
                answer = asyncio.Future()
                task = self.ctx.bot.loop.create_task(message_waiter(answer))
                try:
                    async with async_timeout.timeout(60):
                        while not answer.done():
                            await asyncio.sleep(0)
                except asyncio.TimeoutError:
                    raise
                else:
                    answers.append(answer.result())
                finally:
                    task.cancel()
            return answers

    class Asker:
        def __init__(self, ctx: commands.Context, *args, choices: tuple = tuple(), react_with_choice=False):
            self.ctx = ctx
            self.choices = []
            for choice in args + choices:
                if hasattr(choice, 'discord_str'):
                    self.choices.append(choice.discord_str())
                else:
                    self.choices.append(str(choice))
            if len(self.choices) > 9:
                raise ValueError("Amount of choices can't exceed 9")
            if not self.choices:
                raise ValueError("Amount of choices can't be 0")

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

            if len(self.choices) == 1:
                self.chosen = 0
                return self.chosen

            async def stop_waiter(msg: discord.Message, choice_fut: asyncio.Future):
                def stop_check(r: discord.Reaction, u: discord.User):
                    return all([
                        u.id == self.ctx.author.id,
                        r.message.id == msg.id,
                        r.emoji == '\u274c'
                    ])

                reaction, user = await self.ctx.bot.wait_for('reaction_add', check=stop_check)
                try:
                    choice_fut.set_result(None)
                except asyncio.InvalidStateError:
                    return

            async def reaction_waiter(msg: discord.Message, choice_fut: asyncio.Future):
                def reaction_check(r: discord.Reaction, u: discord.User):
                    return all([
                        u.id == self.ctx.author.id,
                        r.message.id == msg.id,
                        0 < Helper.reaction_to_number(r.emoji) <= len(self.choices)
                    ])

                reaction, user = await self.ctx.bot.wait_for('reaction_add', check=reaction_check)
                try:
                    choice_fut.set_result(Helper.reaction_to_number(reaction.emoji))
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
                description="\n".join([
                    f"**{Helper.number_to_reaction(i+1)}**: {self.choices[i]}" for i in range(len(self.choices))
                ]).strip()
            )
            asker = await self.ctx.send(embed=emb)
            fut = asyncio.Future()
            reaction_task = self.ctx.bot.loop.create_task(reaction_waiter(asker, fut))
            message_task = self.ctx.bot.loop.create_task(message_waiter(fut))
            stop_task = self.ctx.bot.loop.create_task(stop_waiter(asker, fut))
            await asker.add_reaction('\u274c')
            if self.ctx.channel.permissions_for(self.ctx.me).add_reactions:
                for em in map(Helper.number_to_reaction, range(1, len(self.choices) + 1)):
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
                raise
            else:
                if not fut.result():
                    raise asyncio.TimeoutError
                else:
                    self.chosen = fut.result() - 1
                    return self.chosen
            finally:
                reaction_task.cancel()
                message_task.cancel()
                stop_task.cancel()
                if message_exists:
                    await asker.delete()

    class AppendOrSend:
        def __init__(self, channel: discord.abc.Messageable):
            self.data = ""
            self.joining_data = ""
            self.channel = channel

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.flush()

        def _get_all(self):
            return self.data + self.joining_data

        async def append(self, arg: str):
            if self.joining_data:
                self.data = self._get_all()
                self.joining_data = ""
            if not isinstance(arg, str):
                arg = str(arg)
            if len(self._get_all()) + len(arg) > 2000:
                await self.flush()
                self.data = arg
            else:
                self.data += arg

        async def append_join(self, arg: str, join_str: str = ", "):
            if not isinstance(arg, str):
                arg = str(arg)
            if len(self._get_all()) + len(join_str + arg) > 2000:
                await self.flush()
                self.joining_data = arg
            else:
                if self.joining_data:
                    self.joining_data += join_str
                self.joining_data += arg

        async def flush(self):
            if self._get_all():
                await self.channel.send(self._get_all())
            self.data = ""
            self.joining_data = ""

    # endregion


def setup(bot: 'alice.Alice'):
    bot.helper = Helper()


def teardown(bot: 'alice.Alice'):
    bot.helper = None
