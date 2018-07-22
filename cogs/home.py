import aiohttp.web
import asyncio

import datetime
import discord

import alice


class Home:
    def __init__(self, bot: alice.Alice, routes):
        self.bot = bot
        self.app = aiohttp.web.Application(loop=self.bot.loop)
        self.app.bot = bot
        self.app.add_routes(routes)
        coro = self.bot.loop.create_server(self.app._make_handler(loop=self.app.loop),
                                           host='0.0.0.0',
                                           port=80)
        self.server_fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

    def __unload(self):
        asyncio.run_coroutine_threadsafe(self.unloader(), self.bot.loop)

    async def unloader(self):
        while not self.server_fut.done():
            await asyncio.sleep(0)
        self.server_fut.result().close()


def setup(bot):
    s_routes = aiohttp.web.RouteTableDef()

    @s_routes.post("/api/webhooks/dblVote")
    async def vote_handler(request: aiohttp.web.Request):
        bot: alice.Alice = request.app.bot
        if request.headers.get('Authorization') != bot.config.get('vote_webhook_auth'):
            return aiohttp.web.Response(text='Unauthorized', status=401)
        else:
            jj = await request.json()
            webhook: discord.Webhook = await bot.get_webhook_info(bot.config.get('vote_webhook_id'))
            user = bot.get_user(jj['user'])
            if not user:
                user = await bot.get_user_info(jj['user'])
            emb = discord.Embed(description=f"Thank you for voting for me{', '+user.mention if user else ''}.")
            # TODO: Add votes to database over here.
            emb.set_author(name=user.name if user else 'Unknown User',
                           icon_url=user.avatar_url if user else bot.user.default_avatar_url)
            if jj['type'] == 'test':
                emb.set_footer(text="This was a test vote")
            else:
                emb.set_footer(text=datetime.datetime.now().strftime('%y-%m-%d %H:%M'))
            await webhook.send(embed=emb)
            return aiohttp.web.Response(text="Success")

    bot.add_cog(Home(bot, s_routes))
