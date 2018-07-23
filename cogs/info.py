import discord
from discord.ext import commands

import alice
import re


class Info:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

    # region Whois

    async def info_giver(self, ctx, member: discord.Member = None):
        if member is None:
            if ctx.guild is not None:
                member = ctx.guild.get_member(self.bot.user.id)
            else:
                member = ctx.channel.me
        emb = discord.Embed()
        emb.set_author(name="Whois for {}#{}".format(member.display_name, member.discriminator),
                       icon_url=member.avatar_url)
        emb.set_thumbnail(url=member.avatar_url)
        emb.add_field(name="**ID**", value=member.id)
        emb.add_field(name="**Joined Discord**",
                      value=discord.utils.snowflake_time(member.id).strftime('%Y-%m-%d %H:%M'))
        try:
            emb.add_field(name="**Color**", value=str(member.color))
            emb.add_field(name="**Joined {}**".format(member.guild.name)[:256],
                          value=member.joined_at.strftime('%Y-%m-%d %H:%M'))
            if member.activity:
                emb.add_field(name="**Status**",
                              value=f'{member.activity.type.name.capitalize()} {member.activity.name}')
            roles = ", ".join([r.name for r in member.roles])
            if len(roles) < 500:
                emb.add_field(name="**Roles**", value=roles)
        except:
            pass
        emb.add_field(name="**Avatar url**", value="[Here]({})".format(member.avatar_url))
        try:
            await ctx.send(embed=emb)
        except:
            await ctx.send("Too much info...")

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def whois(self, ctx, member: discord.Member = None):
        """
        Displays information about a given member
        """
        await self.info_giver(ctx, member)

    @whois.command()
    @commands.bot_has_permissions(embed_links=True)
    async def owner(self, ctx):
        await ctx.send("Use ``serverowner`` or ``botowner`` instead")

    @whois.command()
    @commands.bot_has_permissions(embed_links=True)
    async def botowner(self, ctx):
        try:
            owner = ctx.guild.get_member(self.bot.owner_id)
        except:
            owner = self.bot.get_user(self.bot.owner_id)
        await self.info_giver(ctx, owner)

    @whois.command()
    @commands.bot_has_permissions(embed_links=True)
    async def serverowner(self, ctx):
        if ctx.guild is None:
            await ctx.send("Can't do that in here")
            return
        await self.info_giver(ctx, ctx.guild.owner)

    @whois.command()
    @commands.bot_has_permissions(embed_links=True)
    async def you(self, ctx):
        await self.info_giver(ctx, None)

    @whois.command()
    @commands.bot_has_permissions(embed_links=True)
    async def me(self, ctx):
        await self.info_giver(ctx, ctx.author)

    # endregion

    @commands.command(aliases=['emoteinfo'])
    async def emojiinfo(self, ctx: commands.Context, request: str):
        if not re.match('<a?:.+:\d+>', request):
            await ctx.send("I'm afraid that isn't an emoji")
        else:
            emoji_id = int(''.join([i for i in request if i.isdigit()]))
            emoji = discord.utils.get(self.bot.emojis, id=emoji_id)
            if not emoji or ctx.author not in emoji.guild.members:
                await ctx.send("We are not both in the server where that emoji is from")
            else:
                await ctx.send(f"That emoji is from {emoji.guild.name}")

    @commands.command(aliases=['mutualguilds'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def mutualservers(self, ctx):
        async with self.bot.helper.AppendOrSend(ctx) as appender:
            await appender.append('We are both in these servers:\n')
            for guild in self.bot.guilds:
                if ctx.author in guild.members:
                    safe_name = guild.name.replace("`", "\u02cb")
                    await appender.append_join(f"``{safe_name}``")


    @mutualservers.error
    async def servers_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            if await self.bot.is_owner(ctx.author):
                await ctx.reinvoke()
                return
        else:
            await self.bot.helper.handle_error(ctx, error)


def setup(bot):
    bot.add_cog(Info(bot))
