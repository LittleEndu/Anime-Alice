import os

import asyncio

import discord
from discord.ext import commands

import alice


class Admin:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

    @commands.command(aliases=['git'], hidden=True)
    @commands.is_owner()
    async def gitreload(self, ctx: commands.Context):
        fut = self.bot.loop.run_in_executor(self.bot.executor, os.system, 'git pull')
        while not fut.done():
            await asyncio.sleep(0)
        if not fut.result() == 0:
            await ctx.send('There was an error pulling from git')
            return
        await ctx.send('Successfully pulled from git')
        reload = self.bot.get_command('reload')
        await reload.callback(self.bot, ctx)

    @commands.command(aliases=['doas', 'as'], hidden=True)
    @commands.is_owner()
    async def su(self, ctx: commands.Context, member: discord.Member, *, command: str):
        prefixes = await self.bot.get_prefix(ctx.message)
        for pre in prefixes:
            if command.startswith(pre):
                break
        else:
            await ctx.send("That's not a valid way to trigger a command")
            return
        await ctx.send(f'Running that command as {member.display_name}')
        msg: discord.Message = await ctx.send(command)
        msg.author = member
        await self.bot.process_commands(msg)

    @commands.command(hidden=True, aliases=['exit', 'die', 'kys'])
    @commands.is_owner()
    async def restart(self, ctx: commands.Context, *, reason: str = None):
        if not reason:
            await ctx.send('You must provide a reason')
            return
        with open('exit_reason', 'w') as out_file:
            out_file.write(reason)
        with open('exit_channel', 'w') as out_file:
            out_file.write(str(ctx.channel.id))
        if not await self.bot.helper.react_or_false(ctx, '\U0001f44b'):
            await ctx.send('\U0001f44b')
        await self.bot.change_presence(status=discord.Status.invisible)
        raise KeyboardInterrupt

def setup(bot):
    bot.add_cog(Admin(bot))
