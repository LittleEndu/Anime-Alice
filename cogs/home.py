import aiohttp.web
import asyncio

import datetime
import discord

import alice


class Home:
    def __init__(self, bot: alice.Alice, routes):
        self.bot = bot
        self.my_guild = discord.utils.get(self.bot.guilds, owner=self.bot.user)
        self.app = aiohttp.web.Application(loop=self.bot.loop)
        self.app.bot = bot
        self.app.add_routes(routes)
        coro = self.bot.loop.create_server(self.app._make_handler(loop=self.app.loop),
                                           host='0.0.0.0',
                                           port=80)
        self.server_fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        self.bot.loop.create_task(self.db_init())

    async def db_init(self):
        await self.bot.database.wait_for_start()
        await self.bot.database.create_votes_table()

    def __unload(self):
        asyncio.run_coroutine_threadsafe(self.unloader(), self.bot.loop)

    async def unloader(self):
        while not self.server_fut.done():
            await asyncio.sleep(0)
        self.server_fut.result().close()

    async def punish_hoisters(self, member: discord.Member):
        if member.guild == self.my_guild:
            name = member.display_name
            while name < '0':
                name = name[1:]
            if name != member.display_name:
                if name:
                    await member.edit(nick=name)
                else:
                    await member.edit(nick="\u2744")

    # region events
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        await self.punish_hoisters(after)

    async def on_member_join(self, member: discord.Member):
        await self.punish_hoisters(member)
    # endregion
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
