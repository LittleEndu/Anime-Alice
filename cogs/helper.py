import traceback

import asyncio
import math

import async_timeout
import discord
from discord.ext import commands


# region discord stuff
if False:
    import alice


class Helper:
    @staticmethod
    async def handle_error(ctx, err):
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
            ctx.bot.logger.debug("".join(traceback.format_exception(type(err), err.__cause__, err.__cause__.__traceback__)))

    @staticmethod
    async def react_or_false(ctx, reactions=("\u2705",)):
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
        return f"{number}\u20E3"

    @staticmethod
    def reaction_to_number(reaction: str):
        try:
            return int(reaction[0])
        except:
            return None


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

            async def reaction_waiter(msg: discord.Message, choice_fut: asyncio.Future):
                def reaction_check(r: discord.Reaction, u: discord.User):
                    return all([
                        u.id == self.ctx.author.id,
                        r.message.id == msg.id,
                        0 < Helper.reaction_to_number(r.emoji) <= len(self.choices)])

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
                description="\n".join([f"**{i+1}**: {self.choices[i]}" for i in range(len(self.choices))]).strip()
            )
            asker = await self.ctx.send(embed=emb)
            fut = asyncio.Future()
            reaction_task = self.ctx.bot.loop.create_task(reaction_waiter(asker, fut))
            message_task = self.ctx.bot.loop.create_task(message_waiter(fut))
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
                self.chosen = fut.result() - 1
                return self.chosen
            finally:
                reaction_task.cancel()
                message_task.cancel()
                if message_exists:
                    await asker.delete()


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

    # endregion

def setup(bot: 'alice.Alice'):
    bot.helper = Helper()

def teardown(bot: 'alice.Alice'):
    bot.helper = None