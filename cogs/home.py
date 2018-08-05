import aiohttp.web
import asyncio

import datetime
import discord
from discord.ext import commands
from io import BytesIO

import alice
from cogs import error_handler


def owner_or_has_perms(**kwargs):
    async def inner(ctx: commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True

        ch = ctx.channel
        permissions = ch.permissions_for(ctx.author)

        missing = [perm for perm, value in kwargs.items() if getattr(permissions, perm, None) != value]

        if not missing:
            return True

        raise commands.MissingPermissions(missing)

    return commands.check(inner)


class OnlyMyGuild(commands.CheckFailure):
    pass


class OnlyMyGuildHandler(error_handler.DefaultHandler):
    def __init__(self, priority=10):
        super().__init__(priority)

    async def handle(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, OnlyMyGuild):
            await ctx.bot.helper.react_or_false(ctx, ("\u2753",))
        else:
            await super().handle(ctx, err)


class Home:
    def __init__(self, bot: alice.Alice, routes):
        self.bot = bot
        self.my_guild = None
        self.app = aiohttp.web.Application(loop=self.bot.loop)
        self.app.bot = bot
        self.app.add_routes(routes)
        # noinspection PyProtectedMember
        coro = self.bot.loop.create_server(self.app._make_handler(loop=self.app.loop),
                                           host='0.0.0.0',
                                           port=1025)
        # We are not using AppRunner API because it won't let us use the bot loop.
        # Not a problem when the bot loop is same as default event loop, but still
        self.server_fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        self.bot.loop.create_task(self.db_init())
        err_cog: error_handler.ErrorCog = self.bot.get_cog('ErrorCog')
        if err_cog:
            err_cog.add_handler(OnlyMyGuildHandler())

    async def db_init(self):
        await self.bot.database.wait_for_start()
        await self.bot.database.create_votes_table()

    def __unload(self):
        asyncio.run_coroutine_threadsafe(self.unloader(), self.bot.loop)

    def __local_check(self, ctx):
        if ctx.guild != self.my_guild:
            raise OnlyMyGuild()
        return True

    async def unloader(self):
        while not self.server_fut.done():
            await asyncio.sleep(0)
        self.server_fut.result().close()

    # region events
    async def punish_hoisters(self, member: discord.Member):
        if self.my_guild is None:
            await self.bot.wait_until_ready()
            self.my_guild = discord.utils.get(self.bot.guilds, owner=self.bot.user)
        if member.guild == self.my_guild:
            name = member.display_name
            while name and name < 'A':
                name = name[1:]
            if name != member.display_name:
                if name:
                    await member.edit(nick=name)
                else:
                    await member.edit(nick="\u2744")

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        await self.punish_hoisters(after)

    async def on_member_join(self, member: discord.Member):
        await self.punish_hoisters(member)

    # endregion

    @commands.command(aliases=['addemote'])
    @owner_or_has_perms(manage_emojis=True)
    async def addemoji(self, ctx: commands.Context, name: str):
        if len(ctx.message.attachments) == 0:
            raise commands.UserInputError('You must attach an image')
        if len(ctx.message.attachments) > 1:
            raise commands.UserInputError('You must attach only one image')
        emj: discord.Emoji = discord.utils.get(ctx.guild.emojis, name=name)
        if emj:
            await emj.delete(reason='Updating this emoji')
        buffer = BytesIO()
        await ctx.message.attachments[0].save(buffer)
        buffer.seek(0)
        rv = await ctx.guild.create_custom_emoji(name=name, image=buffer.read())
        await self.bot.helper.react_or_false(ctx, reactions=(rv,))

    # end class


def setup(bot):
    s_routes = aiohttp.web.RouteTableDef()

    @s_routes.post("/api/webhooks/dblVote")
    async def vote_handler(request: aiohttp.web.Request):
        bot: alice.Alice = request.app.bot

        if request.headers.get('Authorization') != bot.config.get('vote_webhook_auth'):
            bot.logger.debug("Unauthorized request to dblVote webhook")
            return aiohttp.web.Response(text='Unauthorized', status=401)
        elif bot.database is None:
            return aiohttp.web.Response(text=":shrug:")
        else:
            jj = await request.json()
            jj['user'] = int(jj['user'])
            bot.logger.debug(f"Request to dblVote webhook: {jj}")
            channel: discord.TextChannel = bot.get_channel(bot.config.get('vote_channel_id'))
            user = bot.get_user(jj['user'])
            if not user:
                user = await bot.get_user_info(jj['user'])
            emb = discord.Embed(description=f"Thank you for voting for me{', '+user.mention if user else ''}.")
            await bot.database.add_vote(jj['user'])
            emb.set_author(name=user.name if user else 'Unknown User',
                           icon_url=user.avatar_url if user else bot.user.default_avatar_url)
            if jj['type'] == 'test':
                emb.set_footer(text="This was a test vote")
            else:
                emb.set_footer(text=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
            await channel.send(embed=emb)
            return aiohttp.web.Response(text="Success")

    bot.add_cog(Home(bot, s_routes))
