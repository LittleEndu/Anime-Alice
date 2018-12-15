import re

import discord
from discord.ext import commands

import alice


class GuildChannelConverter(commands.Converter):
    def convert(self, ctx, argument):
        return commands.TextChannelConverter().convert(ctx, argument) \
               or commands.CategoryChannelConverter().convert(ctx, argument) \
               or commands.VoiceChannelConverter().convert(ctx, argument)


class Info:
    def __init__(self, bot: alice.Alice):
        self.bot = bot

    # region Whois

    async def info_giver(self, ctx, member: discord.Member = None):
        if member is None:
            if ctx.guild:
                member = ctx.guild.get_member(self.bot.user.id)
            else:
                member = ctx.channel.me
        if ctx.guild:
            emb = discord.Embed(colour=member.top_role.colour)
        else:
            emb = discord.Embed()
        emb.set_author(name="Whois for {}#{}".format(member.display_name, member.discriminator),
                       icon_url=member.avatar_url)
        emb.set_thumbnail(url=member.avatar_url)
        emb.add_field(name="ID", value=member.id)
        emb.add_field(name="Joined Discord",
                      value=discord.utils.snowflake_time(member.id).strftime('%Y-%m-%d %H:%M'))
        try:
            emb.add_field(name="Color", value=str(member.color))
            emb.add_field(name="Joined {}".format(self.bot.helper.safety_escape_monospace(member.guild.name))[:256],
                          value=member.joined_at.strftime('%Y-%m-%d %H:%M'))
            if member.activity:
                emb.add_field(name="Status",
                              value=f'{member.activity.type.name.capitalize()} {member.activity.name}')
            roles = ", ".join([r.mention for r in member.roles[1:]])
            if roles and len(roles) < 500:
                emb.add_field(name="Roles", value=roles)
        except:
            pass
        emb.add_field(name="Avatar url", value="[Here]({})".format(member.avatar_url_as(static_format='png')))
        try:
            await ctx.send(embed=emb)
        except:
            await ctx.send("Too much info...")

    @commands.group(invoke_without_command=True, case_insensitive=True)
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

    @whois.command(aliases=['yourowner'])
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
        """Shows where the given emoji is from"""
        emoji_id = None
        if re.match('<a?:.+:\d+>', request):
            emoji_id = int(''.join([i for i in request if i.isdigit()]))
        else:
            try:
                emoji_id = int(request)
            except ValueError:
                pass
        if emoji_id:
            emoji = discord.utils.get(self.bot.emojis, id=emoji_id)
            if not emoji or ctx.author not in emoji.guild.members and not self.bot.is_owner(ctx.author):
                await ctx.send("We are not both in the server where that emoji is from")
            else:
                await ctx.send(f"That emoji is from {self.bot.helper.safety_escape_monospace(emoji.guild.name)}")
        else:
            await ctx.send("I'm afraid that isn't a custom emoji")

    @commands.command(aliases=['mutualguilds'])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def mutualservers(self, ctx, member: discord.Member = None):
        """Shows the servers both the bot and the user are in"""
        appender = self.bot.helper.AppendOrSend(ctx)
        if member and not await self.bot.is_owner(ctx.author):
            await ctx.send("I won't show you servers some other person is in")
            return
        elif member:
            appender = self.bot.helper.AppendOrSend(ctx.author)
            await self.bot.helper.react_or_false(ctx, "\U0001f4eb")
        async with appender:
            await appender.append('We are both in these servers:\n')
            for guild in self.bot.guilds:
                if member:
                    if member in guild.members:
                        await appender.append_join(self.bot.helper.safety_escape_monospace(guild.name))
                elif ctx.author in guild.members:
                    await appender.append_join(self.bot.helper.safety_escape_monospace(guild.name))

    @mutualservers.error
    async def servers_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown) and await self.bot.is_owner(ctx.author):
            await ctx.reinvoke()
            return
        else:
            await self.bot.get_cog('ErrorCog').error_handler.handle(ctx, error)

    @commands.command(aliases=['permissionsfor'])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, external_emojis=True)
    async def permissions(self, ctx, member: discord.Member = None):
        """Shows what are the users permissions"""
        perms = [name for name in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, name), property)]
        if member is None:
            member = ctx.me
        member_perms = member.guild_permissions
        field = [[], []]
        yes = '\U00002705'
        no = self.bot.get_emoji(473537506063810561)
        index = 0
        for perm in perms:
            value = no
            if getattr(member_perms, perm):
                value = yes
            # noinspection PyTypeChecker
            field[index % 2].append(f"{value} {perm.replace('_',' ').capitalize()}\u200b \u200b")
            index += 1
        emb = discord.Embed()
        emb.add_field(name="Here are the permissions:\u200b \u200b", value="\n".join(field[0]))
        emb.add_field(name="\u200b", value="\n".join(field[1]))
        emb.set_footer(text=f"Permissions for {member.display_name} in {ctx.guild.name}")
        await ctx.send(embed=emb)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, external_emojis=True)
    async def permissionsin(self, ctx, channel: GuildChannelConverter, member: discord.Member = None):
        """Shows what are the users permissions"""
        assert isinstance(channel, discord.abc.GuildChannel)
        perms = [name for name in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, name), property)]
        if member is None:
            member = ctx.me
        member_perms = channel.permissions_for(member)
        field = [[], []]
        yes = '\U00002705'
        no = self.bot.get_emoji(473537506063810561)
        index = 0
        for perm in perms:
            value = no
            if getattr(member_perms, perm):
                value = yes
            # noinspection PyTypeChecker
            field[index % 2].append(f"{value} {perm.replace('_',' ').capitalize()}\u200b \u200b")
            index += 1
        emb = discord.Embed()
        emb.add_field(name="Here are the permissions:\u200b \u200b", value="\n".join(field[0]))
        emb.add_field(name="\u200b", value="\n".join(field[1]))
        # noinspection PyUnresolvedReferences
        emb.set_footer(text=f"Permissions for {member.display_name} in {channel.name}")
        await ctx.send(embed=emb)


def setup(bot):
    bot.add_cog(Info(bot))
