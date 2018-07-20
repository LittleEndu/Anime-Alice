import asyncio
import concurrent.futures
import importlib
import inspect
import io
import itertools
import json
import logging
import os
import os.path
import shutil
import sys
import textwrap
import traceback
from contextlib import redirect_stdout, redirect_stderr
from logging.handlers import RotatingFileHandler

import aiohttp
import discord
from discord.ext import commands

import helper


class Alice(commands.Bot):
    def __init__(self, config_name='config.json'):
        super().__init__(command_prefix=_prefix)
        self._config_name = config_name

        # Get config and set other initial variables
        if not os.path.isfile(config_name):
            shutil.copy('exampleconfig.json', config_name)
        with open(config_name) as file_in:
            config = json.load(file_in)
        self.config = config
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.database = helper.Database(self,
                                        config.get('DB_host'),
                                        config.get('DB_name'),
                                        config.get('DB_user'),
                                        config.get('DB_password'))

        # Setup logging
        if not os.path.isdir("logs"):
            os.makedirs("logs")
        root_logger = logging.getLogger()
        self.logger = logging.getLogger('alice')
        formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)-8s %(message)s')

        fh = RotatingFileHandler("logs/alice.log", maxBytes=1000000)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        dh = RotatingFileHandler("logs/debug.log", maxBytes=1000000)
        dh.setLevel(1)
        dh.setFormatter(formatter)
        th = RotatingFileHandler("logs/trace.log", maxBytes=1000000)
        th.setLevel(1)
        th.setFormatter(formatter)
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)

        root_logger.addHandler(fh)
        root_logger.addHandler(sh)
        root_logger.addHandler(dh)
        root_logger.setLevel(1)

        self.logger.addHandler(th)
        self.logger.setLevel(1)

        # Remove default help and add other commands
        self.remove_command("help")
        for i in [self.reload, self.load, self.unload, self.debug, self.loadconfig, self._latency, self._exec]:
            self.add_command(i)
        self._last_result = None

    async def start(self, *args, **kwargs):
        await self.database.start()
        await super().start(*args, **kwargs)

    async def on_ready(self):
        self.logger.info('Logged in as')
        self.logger.info(self.user.name)
        self.logger.info(f"id:{self.user.id}")
        self.logger.info(f"{len(self.commands)} commands")
        self.logger.info('------')

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id != self.owner_id:
            return
        if str(payload.emoji) == '\U0001f502':
            message = await self.get_channel(payload.channel_id).get_message(payload.message_id)
            if payload.guild_id:
                message.author = self.get_guild(payload.guild_id).get_member(payload.user_id)
            else:
                message.author = self.get_user(payload.user_id)
            ctx = await self.get_context(message)
            if ctx.command:
                if ctx.command.name in ['debug', 'exec']:
                    try:
                        await message.remove_reaction(payload.emoji, discord.Object(payload.user_id))
                    except discord.Forbidden:
                        pass
                    msg = await ctx.send(message.content)
                    ctx.re_runner = msg
                    await ctx.reinvoke()

    async def get_prefix(self, message: discord.Message):
        if isinstance(message.channel, discord.DMChannel):
            return [
                f'{message.channel.me.mention} ',
                "".join(itertools.takewhile(lambda k: not k.isalnum(), message.content))
            ]  # mention needs to be first to get triggered
        return await super().get_prefix(message)

    async def on_command_error(self, ctx: commands.Context, err):
        if hasattr(ctx.command, "on_error"):
            return
        await helper.handle_error(ctx, err)

    # region Commands

    @commands.command(aliases=['reloadall', 'loadall'], hidden=True)
    @commands.is_owner()
    async def reload(self, ctx):
        for ext in set([i.replace("cogs.", "") for i in self.extensions.keys()] + self.config.get('auto_load', [])):
            await self.load_cog(ctx, ext, True)
        await ctx.send("Reloaded already loaded cogs and cogs under auto_load")

    async def load_cog(self, ctx, extension, silent=False):
        self.logger.info("Loading " + extension)
        try:
            importlib.import_module("cogs.{}".format(extension))
        except Exception as err:
            self.logger.error("".join(traceback.format_exception(type(err), err.__cause__, err.__traceback__)))
            await ctx.send("Can not load `{}` -> `{}`".format(extension, err))
            return
        try:
            self.unload_extension("cogs.{}".format(extension))
        except:
            pass
        try:
            self.load_extension("cogs.{}".format(extension))
        except Exception as err:
            self.logger.error("".join(traceback.format_exception(type(err), err.__cause__, err.__traceback__)))
            await ctx.send("\u26a0 Could not load `{}` -> `{}`".format(extension, err))
        else:
            if not silent and not await helper.react_or_false(ctx):
                await ctx.send("Loaded `{}`.".format(extension))

    @commands.command(hidden=True, aliases=['reloadconfig', 'reloadjson', 'loadjson'])
    @commands.is_owner()
    async def loadconfig(self, ctx):
        """
        Reload the config
        """
        try:
            with open(self._config_name) as file_in:
                config = json.load(file_in)
            self.config = config
            if not await helper.react_or_false(ctx):
                await ctx.send("Successfully loaded config")
        except Exception as err:
            await ctx.send("Could not reload config: `{}`".format(err))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, extension: str):
        """
        Load an extension.
        """
        await self.load_cog(ctx, extension)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, extension: str):
        """Unloads an extension."""
        self.logger.info("Unloading " + extension)
        try:
            self.unload_extension("cogs.{}".format(extension))
        except Exception as err:
            self.logger.error("".join(traceback.format_exception(type(err), err.__cause__, err.__traceback__)))
            await ctx.send("Could not unload `{}` -> `{}`".format(extension, err))
        else:
            if not await helper.react_or_false(ctx):
                await ctx.send("Unloaded `{}`.".format(extension))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def debug(self, ctx, *, command: str):
        """
        Runs a debug command
        """
        self.logger.debug(f"Running debug command: {ctx.message.content}")
        env = {
            'bot': self,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())

        has_been_awaited = False
        result_class = None
        try:
            result = eval(command, env)
            if inspect.isawaitable(result):
                has_been_awaited = True
                result = await result
            if result is not None:
                self._last_result = result
        except Exception as err:
            result = repr(err)
            result_class = "{}.{}".format(err.__class__.__module__, err.__class__.__name__)
        if result_class is None:
            result_class = "{}.{}".format(result.__class__.__module__, result.__class__.__name__)
        result_too_big = len(str(result)) > 2000

        safe_result = str(result)
        for sens in [self.config.get(i) for i in self.config.get('unsafe_to_expose')]:
            safe_result = str(safe_result).replace(sens, '\u2588' * 10)

        if ctx.channel.permissions_for(ctx.me).embed_links:
            color = discord.Color(0)
            if isinstance(result, discord.Colour):
                color = result
            emb = discord.Embed(description="{}".format(safe_result)[:2000],
                                color=color)
            emb.set_footer(text="{} {} {}".format(
                result_class,
                "| Command has been awaited" if has_been_awaited else "",
                "| Result has been cut" if result_too_big else "")
            )
            await ctx.send(embed=emb)
        else:
            await ctx.send("```xl\nOutput: {}\nOutput class: {} {} {}```".format(
                str(safe_result).replace("`", "\u02cb")[:1500],
                result_class,
                "| Command has been awaited" if has_been_awaited else "",
                "| Result has been cut" if result_too_big else ""))
        if hasattr(ctx, 'rerunner'):
            try:
                await ctx.re_runner.add_reaction('\U0001f502')
            except discord.Forbidden:
                pass
        await helper.react_or_false(ctx, ['\U0001f502'])

    async def send_or_post_hastebin(self, ctx: commands.Context, content: str):
        try:
            await ctx.send(content)
        except discord.HTTPException:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        'https://hastebin.com/documents',
                        data="\n".join(content.splitlines()[1:-1])
                ) as response:
                    if response.status == 200:
                        jj = json.loads(await response.text())
                        await ctx.send(f"https://hastebin.com/{jj.get('key')}")
                    else:
                        await ctx.send(f"Result too big and hastebin responded with {response.status}")

    @commands.command(hidden=True, name='exec')
    @commands.is_owner()
    async def _exec(self, ctx, *, body: str):
        """
        Evaluates a piece of code
        Shamelessly stolen from R.Danny because its license is MIT
        """

        self.logger.debug(f"Running exec command: {ctx.message.content}")
        env = {
            'bot': self,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())

        if body.startswith('```') and body.endswith('```'):
            body = '\n'.join(body[:-3].split('\n')[1:])
        body = body.strip('` \n')
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await self.send_or_post_hastebin(ctx, f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stderr(stdout):
                with redirect_stdout(stdout):
                    ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await self.send_or_post_hastebin(ctx, f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            if not await helper.react_or_false(ctx):
                await ctx.send('\u2705')
            if hasattr(ctx, 're_runner'):
                try:
                    await ctx.re_runner.add_reaction('\u2705')
                except discord.Forbidden:
                    await ctx.send('\u2705')

            for sens in [self.config.get(i) for i in self.config.get('unsafe_to_expose')]:
                value = str(value).replace(sens, '\u2588' * 10)

            if ret is None:
                if value:
                    value = value.replace("`", "\u02cb")
                    await self.send_or_post_hastebin(ctx, f'```py\n{value}\n```')
            else:
                self._last_result = ret
                for sens in [self.config.get(i) for i in self.config.get('unsafe_to_expose')]:
                    ret = str(ret).replace(sens, '\u2588' * 10)
                ret = ret.replace("`", "\u02cb")
                await self.send_or_post_hastebin(ctx, f'```py\n{value}{ret}\n```')
        await helper.react_or_false(ctx, ['\U0001f502'])
        if hasattr(ctx, 're_runner'):
            try:
                await ctx.re_runner.add_reaction('\U0001f502')
            except discord.Forbidden:
                pass

    @commands.command(name='latency', aliases=['ping', 'marco', 'hello', 'hi', 'hey'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def _latency(self, ctx):
        """Reports bot latency"""
        if ctx.invoked_with == 'ping':
            msg = await ctx.send("Pong")
        elif ctx.invoked_with == 'marco':
            msg = await ctx.send("Polo")
        elif ctx.invoked_with in ['hello', 'hi', 'hey']:
            msg = await ctx.send("Hey")
        else:
            msg = await ctx.send("\u200b")
        latency = msg.created_at.timestamp() - ctx.message.created_at.timestamp()
        await ctx.send("That took {}ms. Discord reports latency of {}ms".format(int(latency * 1000),
                                                                                int(self.latency * 1000)))

    @_latency.error
    async def latency_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            if await self.is_owner(ctx.author):
                await ctx.reinvoke()
                return
        else:
            helper.handle_error(ctx, error)

    # endregion


async def _prefix(bot: Alice, message: discord.Message):
    return commands.when_mentioned_or(*await bot.database.get_prefixes(message))(bot, message)


class RedirectToLog(io.StringIO):
    def __init__(self, level: int = logging.INFO, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.level = level
        self.buffer = ''

    async def flush_task(self):
        while asyncio.get_event_loop().is_running():
            await asyncio.sleep(1)
            if self.buffer:
                logging.getLogger().log(level=self.level, msg=self.buffer)
                self.buffer = ''

    def write(self, *args, **kwargs):
        self.buffer += " ".join(args)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        alice = Alice(config_name=sys.argv[1])
    else:
        alice = Alice()
    err = RedirectToLog(logging.ERROR)
    out = RedirectToLog(logging.INFO)
    tasks = [asyncio.get_event_loop().create_task(err.flush_task()),
             asyncio.get_event_loop().create_task(out.flush_task())]
    try:
        with redirect_stderr(err):
            with redirect_stdout(out):
                alice.logger.info("\n\n\n")
                alice.logger.info(f"Running python version {sys.version}")
                alice.logger.info("Initializing")
                if alice.config.get('token', ''):
                    for ex in alice.config.get('auto_load', []):
                        try:
                            alice.load_extension("cogs.{}".format(ex))
                            alice.logger.info("Successfully loaded {}".format(ex))
                        except Exception as e:
                            alice.logger.info('Failed to load extension {}\n{}: {}'.format(ex, type(e).__name__, e))
                    alice.logger.info("Logging in...\n")
                    alice.run(alice.config.get('token'))
                else:
                    alice.logger.info("Please add the token to the config file!")
                    asyncio.get_event_loop().run_until_complete(alice.close())
    finally:
        for task in tasks:
            task.cancel()
