import alice
import discord
from discord.ext import commands

class HelpCommand:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

    @commands.command(name='commands')
    async def _commands(self, ctx):
        """
        Lists all visible commands
        """
        to_send = ""
        for i in sorted(self.bot.commands, key=lambda a: a.name):
            help_string = i.brief or f'{i.help or ""}'.split("\n")[0]
            new_line = "\n"
            to_append = f"**``{i.name}``**{f'{new_line}{help_string}' if help_string else ''}\n\n" if not i.hidden else ""
            if len(to_send + to_append) > 2000:
                await ctx.author.send(to_send)
                to_send = ""
            to_send += to_append
        if to_send:
            await ctx.author.send(to_send)
        if not await self.bot.helper.react_or_false(ctx, "\U0001f4eb"):
            await ctx.send("Sent you the commands")


def setup(bot: alice.Alice):
    bot.add_cog(HelpCommand(bot))
