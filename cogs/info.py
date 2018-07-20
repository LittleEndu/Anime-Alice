import discord
from discord.ext import commands

import alice


class Info:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

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
    async def you(self, ctx):
        await self.info_giver(ctx, None)

    @whois.command()
    async def me(self, ctx):
        await self.info_giver(ctx, ctx.author)


def setup(bot):
    bot.add_cog(Info(bot))
