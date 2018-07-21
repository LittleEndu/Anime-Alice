import alice
import discord
from discord.ext import commands


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
            no_help = "This command doesnt have help text :/"
            aliases = ""
            if command.aliases:
                aliases = f"[, {', '.join([f'``{i}``' for i in command.aliases])}]"
            await ctx.send(f"``{command.name}``{aliases}\n\n{command.help if command.help else no_help}")

    @commands.command(name='commands')
    async def _commands(self, ctx):
        """
        Lists all visible commands
        """
        async with self.bot.helper.AppendOrSend(ctx.author) as appender:
            for i in sorted(self.bot.commands, key=lambda a: a.name):
                assert isinstance(i, commands.Command)
                new_line = "\n"  # Don't delete, used in nested fstring
                help_string = i.brief or f'{i.help or ""}'.split(new_line)[0]
                show = not i.hidden and await i.can_run(ctx)
                await appender.append(
                    f"**``{i.name}``**{f'{new_line}{help_string}' if help_string else ''}\n\n" if show else ""
                )
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
        emb = discord.Embed(title=f"Heyo. I'm {ctx.me.display_name}",
                            colour=discord.Colour(0xe29b9b),
                            description=f"""
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
        await ctx.send(embed=emb)


def setup(bot: alice.Alice):
    bot.add_cog(HelpCommand(bot))
