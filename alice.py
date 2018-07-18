import asyncio
import concurrent.futures
import datetime
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
from contextlib import redirect_stdout

import aiohttp
import discord
from discord.ext import commands

import helper


class Alice(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=_prefix)

        # Get config and set other initial variables
        if not os.path.isfile("config.json"):
            shutil.copy('exampleconfig.json', 'config.json')
        with open("config.json") as file_in:
            config = json.load(file_in)
        self.config = config
        self.executor = concurrent.futures.ThreadPoolExecutor()
        with open('DB_AUTH') as AUTH_file:
            self.database_session = aiohttp.ClientSession(headers={'auth': AUTH_file.read()}, loop=self.loop)
        self.prefixes_cache = {}

        # Setup logging
        if not os.path.isdir("logs"):
            os.makedirs("logs")
        self.logger = logging.getLogger('Control')
        fh = logging.FileHandler("logs/" + str(datetime.datetime.now().date()) + ".log")
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        self.logger.addHandler(ch)
        self.logger.setLevel(logging.DEBUG)

        # Remove default help and add other commands
        self.remove_command("help")
        for i in [self.reload, self.load, self.unload, self.debug, self.loadconfig, self._latency, self._exec]:
            self.add_command(i)
        self._last_result = None

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
            with open("config.json") as file_in:
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
        if any([(self.config.get(i) in str(result)) if i in self.config.keys() else False
                for i in self.config.get("unsafe_to_expose")]):
            await ctx.send("Doing this would reveal sensitive info!!!")
            return
        else:
            if ctx.channel.permissions_for(ctx.me).embed_links:
                color = discord.Color(0)
                if isinstance(result, discord.Colour):
                    color = result
                emb = discord.Embed(description="{}".format(result)[:2000],
                                    color=color)
                emb.set_footer(text="{} {} {}".format(
                    result_class,
                    "| Command has been awaited" if has_been_awaited else "",
                    "| Result has been cut" if result_too_big else "")
                )
                await ctx.send(embed=emb)
            else:
                await ctx.send("```xl\nOutput: {}\nOutput class: {} {} {}```".format(
                    str(result).replace("`", "\u02cb")[:1500],
                    result_class,
                    "| Command has been awaited" if has_been_awaited else "",
                    "| Result has been cut" if result_too_big else ""))
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

            if ret is None:
                if value:
                    await self.send_or_post_hastebin(ctx, f'```py\n{value}\n```')
            else:
                self._last_result = ret
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
    guild_id = message.guild.id
    if guild_id in bot.prefixes_cache:
        prefixes = bot.prefixes_cache.get(guild_id)
    else:
        prefixes = (await helper.database.get_prefixes(bot.config.get('DB_HOST'), bot.database_session, message)).get(
            'result')
        for prefix in prefixes:
            bot.prefixes_cache.setdefault(guild_id, list()).append(prefix)
    return commands.when_mentioned_or(*prefixes)(bot, message)


if __name__ == '__main__':
    alice = Alice()
    alice.logger.info("\n\n\n")
    alice.logger.info(f"Running python version {sys.version}")
    alice.logger.info("Initializing")
    if alice.config.get('token', ""):
        for ex in alice.config.get('auto_load', []):
            try:
                alice.load_extension("cogs.{}".format(ex))
                alice.logger.info("Successfully loaded {}".format(ex))
            except Exception as e:
                alice.logger.info('Failed to load extension {}\n{}: {}'.format(ex, type(e).__name__, e))
        alice.logger.info("Logging in...\n")
        alice.run(alice.config['token'])
    else:
        alice.logger.info("Please add the token to the config file!")
        asyncio.get_event_loop().run_until_complete(alice.close())
