import asyncio
import concurrent.futures
import time

import discord
import psutil
from discord.ext import commands

import alice


def custom_ljust(value: str, length: int):
    want = length - len(value)
    if want < 1:
        return value
    return " ".join('\u200b' for _ in range(want + 1)) + value


class HelpCommand:
    """Meta commands about the bot"""

    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self.cpu = 0
        self.memory = psutil.virtual_memory().percent
        self.update_task = self.bot.loop.create_task(self.update_stats())

    def __unload(self):
        self.update_task.cancel()

    async def update_stats(self):
        while True:
            try:
                cpu_fut = self.bot.loop.run_in_executor(self.bot.executor, psutil.cpu_percent, 2)
                await asyncio.sleep(2.1)
                while not cpu_fut.done():
                    await asyncio.sleep(0)
                self.cpu += cpu_fut.result()
                self.cpu /= 2
                self.memory += psutil.virtual_memory().percent
                self.memory /= 2
                await asyncio.sleep(10)
            except concurrent.futures.CancelledError:
                break

    async def find_guild_invite(self):
        my_guild = discord.utils.get(self.bot.guilds, owner=self.bot.user)
        guild_invite = None
        for i in my_guild.text_channels:
            invs = await i.invites()
            if invs:
                guild_invite = invs[0]
        if guild_invite is None:
            guild_invite = await my_guild.text_channels[0].create_invite()
        return my_guild, guild_invite

    @commands.command(name='help', hidden=True)
    async def _help(self, ctx, *, name: str = None):
        """
        Used to see help text on commands
        """
        if name is None:
            _, guild_invite = await self.find_guild_invite()
            prefix = ctx.prefix if len(ctx.prefix) < 10 else ""
            await ctx.send(f"If you are reading this it means that I have failed to make my bot intuitive enough.\n"
                           f"You should contact me (alice@anime-alice.moe or join {guild_invite}) so we could fix it.\n"
                           f"\n"
                           f"Or maybe you just wanted to list all commands. Use ``{prefix}commands`` for that.\n"
                           f"You should also look at ``{prefix}description`` for example usage of commands.\n"
                           f"Or if you want help on a specific command, do ``{prefix}help <command name>``.")
        else:
            command = self.bot.get_command(name.lower())
            cog = self.bot.get_cog(name.capitalize())
            if not command:
                if cog:
                    await ctx.send('That is a cog... Give me a command name')
                else:
                    await ctx.send('Unable to find that command')
                return
            help_text = command.help or command.brief or "This command doesnt have help text :/"
            aliases = ""
            if command.aliases:
                aliases = f" [, {', '.join([f'``{i}``' for i in command.aliases])}]"
            await ctx.send(f"``{command.name}``{aliases}\n\n{help_text}")

    @commands.command(name='commands', aliases=['cmds', 'cmd', 'command'])
    async def _commands(self, ctx):
        """
        Lists all visible commands
        """
        try:
            async with self.bot.helper.AppendOrSend(ctx.author) as appender:
                await appender.append("Don't forget to also look at ``description`` command. \n\n")
                last_cog = ""
                sorted_commands = sorted(self.bot.commands, key=lambda a: a.cog_name + a.name)
                command_names = dict()
                cog_names = []
                for i in sorted_commands[:]:
                    assert isinstance(i, commands.Command)
                    can_run = False
                    try:
                        can_run = await i.can_run(ctx)
                    except commands.CheckFailure:
                        pass
                    show = not i.hidden and can_run
                    if not show:
                        sorted_commands.remove(i)

                prefix = ctx.prefix if len(ctx.prefix) < 5 else ""
                for i in sorted_commands:
                    if i.cog_name != last_cog:
                        last_cog = i.cog_name
                        if cog_names:
                            ll = max(map(len, cog_names))
                            for name in cog_names:
                                command_names[name] = custom_ljust(name, ll)
                        cog_names = []
                    cog_names.append(f"{prefix}{i.name}")
                ll = max(map(len, cog_names))
                for name in cog_names:
                    command_names[name] = custom_ljust(name, ll)

                for i in sorted_commands:
                    assert isinstance(i, commands.Command)
                    if i.cog_name != last_cog:
                        last_cog = i.cog_name
                        await appender.append(f"\n```\U0001f916 {last_cog} \U0001f916```")
                    help_string = i.brief or f'{i.help or ""}'.split("\n")[0]
                    await appender.append(
                        f"**``{command_names[f'{prefix}{i.name}']}`` - **{f'{help_string}' if help_string else ''}\n"
                    )
                await appender.append("\n\nDon't forget to also look at ``description`` command.")

        except (discord.HTTPException, discord.Forbidden):
            if not await self.bot.helper.react_or_false(ctx, '\u26a0'):
                await ctx.send('\u26a0 Could not send the DM...')
            return
        if ctx.guild:
            if not await self.bot.helper.react_or_false(ctx, "\U0001f4eb"):
                await ctx.send("Sent you the commands")

    @commands.command(aliases=['about'])
    @commands.bot_has_permissions(embed_links=True)
    async def info(self, ctx):
        """
        Information about the bot
        """
        # Bot: https://discordapp.com/oauth2/authorize?client_id=354974625593032704&scope=bot&permissions=378944
        # Server: http://discord.gg/HheVh3A
        emb = discord.Embed(colour=discord.Colour(0xe29b9b),
                            url='https://discordbots.org/bot/354974625593032704',
                            description=f"""
Heyo. I'm Alice.
I'm just another Discord bot.
I was made by LittleEndu.
I'm coded in discord.py (version {discord.__version__})
I'm currently running on a Scaleway server somewhere.
My aim is to assist you in anything that's related to anime.
I take my info from [AniList](https://anilist.co/).
                                """)
        emb.set_thumbnail(url=ctx.me.avatar_url)

        emb.add_field(name="Bot invite",
                      value="[Here](https://discordapp.com/oauth2/authorize"
                            "?client_id=354974625593032704&scope=bot&permissions=378944)")
        emb.add_field(name="My server invite",
                      value="[{0.name}]({1.url})".format(*await self.find_guild_invite()))
        emb.add_field(name="discordbots.org entry",
                      value=f"[Alice](https://discordbots.org/bot/354974625593032704)")
        emb.add_field(name="Github repo",
                      value="[LittleEndu/Anime-Alice](https://github.com/LittleEndu/Anime-Alice)")

        otaku = self.bot.get_cog('Otaku')
        if otaku:
            stuff = f"{len(set(otaku.mediums.values()))} things to search for"
        else:
            stuff = "Searching disabled"
        emb.set_footer(text=f"{len(self.bot.guilds)} servers, "
                            f"{len(self.bot.commands)} commands, "
                            f"{stuff}")
        await ctx.send(embed=emb)

    @commands.command(aliases=['desc'])
    @commands.bot_has_permissions(embed_links=True)
    async def description(self, ctx: commands.Context):
        """Link to bot's description"""
        emb = discord.Embed(description="[Description on Github]"
                                        "(https://github.com/LittleEndu/Anime-Alice/blob/master/README.md)"
                                        "\n"
                                        "[Description on discordbots]"
                                        "(https://discordbots.org/bot/354974625593032704)")
        await ctx.send(embed=emb)

    @commands.command(aliases=['stats'])
    async def status(self, ctx: commands.Context):
        """Technical information about bot"""
        uptime_value = self.bot.helper.display_time(time.time() - self.bot.real_start_time)
        discord_value = self.bot.helper.display_time(time.time() - self.bot.discord_start_time)
        latency = int(self.bot.latency * 1000)
        if latency > 1000:
            latency = self.bot.helper.display_time(self.bot.latency)
        else:
            latency = str(latency) + ' ms'
        emb = discord.Embed()
        emb.add_field(name='**Current Status**', value=f"""
**``Commands``** - {len(self.bot.commands)} different commands
**``\u200b \u200b \u200bGuilds``** - {len(self.bot.guilds)} guilds
**``\u200b \u200b \u200bUptime``** - {uptime_value}
**``\u200b \u200b \u200bOnline``** - {discord_value}
**``\u200b \u200bLatency``** - {latency}
**``\u200b \u200b \u200b \u200b \u200b \u200bCPU``** - {int(self.cpu)}%
**``\u200b \u200b \u200b \u200b \u200b \u200bRAM``** - {int(self.memory)}%
        """)
        emb.add_field(name='Last restart reason', value=self.bot.exit_reason, inline=False)
        await ctx.send(embed=emb)

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows how long the bot has been running for"""
        # noinspection PyTypeChecker
        await ctx.send(self.bot.helper.display_time(time.time() - self.bot.real_start_time, granularity=None))

    @commands.command()
    async def vote(self, ctx: commands.Context):
        """Shows information about voting on discordbots.org"""
        if ctx.channel.permissions_for(ctx.me).embed_links:
            emb = discord.Embed(colour=discord.Colour(0xe29b9b),
                                title="Voting for me on discordbots.org?",
                                description="Why yes, please do that.\n"
                                            "[Here's a link for it.]"
                                            "(https://discordbots.org/bot/354974625593032704/vote)")
            emb.add_field(name="NB!",
                          value="I grab votes using a webhook, "
                                "meaning I only know about you voting while my HTTP server is running.\n"
                                "So for any benefits (which there are like 0 of) you should vote while I'm not offline")
            emb.set_thumbnail(url=ctx.me.avatar_url)
            await ctx.send(embed=emb)
        else:
            await ctx.send("Voting for me on discordbots.org? Why yes, please do that. Here's a link for that:\n"
                           "<https://discordbots.org/bot/354974625593032704/vote>\n"
                           "**Do note that** I grab votes using a webhook, "
                           "meaning I only know about you voting while my HTTP server is running.\n"
                           "So for any benefits (which there are like 0 of) you should vote while I'm not offline")


def setup(bot: alice.Alice):
    bot.add_cog(HelpCommand(bot))
