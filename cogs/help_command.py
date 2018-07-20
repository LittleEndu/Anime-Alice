import alice
import discord
from discord.ext import commands


class HelpCommand:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

    @commands.command(name='help', hidden=True)
    async def _help(self, ctx, *, name=None):
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
            no_help = "This command doesnt have help text :/"
            await ctx.send(f"{', '.join([f'``{command.name}``']+[f'``{i}``' for i in command.aliases])}\n\n"
                           f"{command.help if command.help else no_help}")

    @commands.command(name='commands')
    async def _commands(self, ctx):
        """
        Lists all visible commands
        """
        async with self.bot.helper.AppendOrSend(ctx.author) as appender:
            for i in sorted(self.bot.commands, key=lambda a: a.name):
                assert isinstance(i, commands.Command)
                if hasattr(i, 'no_help'):
                    continue
                new_line = "\n"  # Don't delete, used in nested fstring
                help_string = i.brief or f'{i.help or ""}'.split(new_line)[0]
                show = not i.hidden and await i.can_run(ctx)
                await appender.append(
                    f"**``{i.name}``**{f'{new_line}{help_string}' if help_string else ''}\n\n" if show else ""
                )
        if not await self.bot.helper.react_or_false(ctx, "\U0001f4eb"):
            await ctx.send("Sent you the commands")


def setup(bot: alice.Alice):
    bot.add_cog(HelpCommand(bot))
