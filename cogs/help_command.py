import time

import alice
import discord
from discord.ext import commands

intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),  # 60 * 60 * 24
    ('hours', 3600),  # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)


def display_time(seconds, granularity=2):
    seconds = int(seconds)
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])


class HelpCommand:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

    @commands.command(name='help', hidden=True)
    async def _help(self, ctx, *, name=None):
        """
        Used to see help text on commands
        """
        if name is None:
            try:
                owner = ctx.guild.get_member(self.bot.owner_id)
            except:
                owner = self.bot.get_user(self.bot.owner_id)
            await ctx.send(f"If you are reading this it means that I have failed to make my bot intuitive enough.\n"
                           f"You should contact me ({owner.name}#{owner.discriminator}) so we could fix it.\n"
                           f"Or maybe you just wanted to list all commands. Use ``{ctx.prefix}commands`` for that.\n"
                           f"Or if you want help on a specific command, do ``{ctx.prefix}help <command name>``.")
        else:
            command = self.bot.get_command(name)
            if not command:
                await ctx.send('Unable to find that command')
                return
            help_text = command.help or command.brief or "This command doesnt have help text :/"
            aliases = ""
            if command.aliases:
                aliases = f"[, {', '.join([f'``{i}``' for i in command.aliases])}]"
            await ctx.send(f"``{command.name}``{aliases}\n\n{help_text}")

    @commands.command(name='commands')
    async def _commands(self, ctx):
        """
        Lists all visible commands
        """
        async with self.bot.helper.AppendOrSend(ctx.author) as appender:
            last_cog = ""
            for i in sorted(self.bot.commands, key=lambda a: a.cog_name + a.name):
                assert isinstance(i, commands.Command)
                can_run = False
                try:
                    can_run = await i.can_run(ctx)
                except commands.CheckFailure:
                    pass
                show = not i.hidden and can_run
                if show:
                    if i.cog_name != last_cog:
                        last_cog = i.cog_name
                        await appender.append(f"\n```\U0001f916 {last_cog} \U0001f916```")
                    new_line = "\n"  # Don't delete, used in nested fstring
                    help_string = i.brief or f'{i.help or ""}'.split(new_line)[0]
                    prefix = ctx.prefix if len(ctx.prefix) < 5 else ""
                    await appender.append(
                        f"**``{prefix}{i.name}`` - **{f'{help_string}' if help_string else ''}\n"
                    )
        if ctx.guild:
            if not await self.bot.helper.react_or_false(ctx, "\U0001f4eb"):
                await ctx.send("Sent you the commands")

    @commands.command(aliases=['about'])
    @commands.bot_has_permissions(embed_links=True)
    async def info(self, ctx):
        """
        Description of the bot
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

        my_guild = discord.utils.get(self.bot.guilds, owner=self.bot.user)
        guild_invite = None
        for i in my_guild.text_channels:
            invs = await i.invites()
            if invs:
                guild_invite = invs[0]
        if guild_invite is None:
            guild_invite = await my_guild.text_channels[0].create_invite()
        emb.add_field(name="My server invite",
                      value=f"[{my_guild.name}]({guild_invite.url})")

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
        emb = discord.Embed(description="[Description on Github]"
                                        "(https://github.com/LittleEndu/Anime-Alice/blob/master/README.md)"
                                        "\n"
                                        "[Description on discordbots]"
                                        "(https://discordbots.org/bot/354974625593032704)")
        await ctx.send(embed=emb)

    @commands.command(aliases=['stats'])
    async def status(self, ctx: commands.Context):
        cmds = self.bot.get_emoji(474599018761289729) or '\U0001f916'
        uptime = self.bot.get_emoji(474628476406726656) or '\U000023f1'
        guild = self.bot.get_emoji(474630189792624650) or '\U0001f6e1'
        uptime_value = display_time(time.time() - self.bot.real_start_time)
        discord_value = display_time(time.time() - self.bot.discord_start_time)
        emb = discord.Embed()
        emb.add_field(name='__**Current Status**__', value=f"""
**{cmds} Commands**
{len(self.bot.commands)} different commands

**{guild} Servers**
{len(self.bot.guilds)} different servers

**{uptime} Uptime**
{uptime_value} since last time bot restarted
{discord_value} since last time discord reconnected
        """)
        await ctx.send(embed=emb)


def setup(bot: alice.Alice):
    bot.add_cog(HelpCommand(bot))
