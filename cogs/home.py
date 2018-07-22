import aiohttp.web
import discord

import alice


class Home:
    def __init__(self, bot: alice.Alice, routes):
        self.bot = bot
        self.app = aiohttp.web.Application(loop=self.bot.loop)
        self.app.bot = bot
        self.app.add_routes(routes)
        self.server = self.bot.loop.create_server(self.app._make_handler(loop=self.app.loop),
                                                  host='0.0.0.0',
                                                  port=80)

    def __unload(self):
        self.server.close()


def setup(bot):
    s_routes = aiohttp.web.RouteTableDef()

    @s_routes.post("/api/webhooks/dblVote")
    async def vote_handler(request):
        assert isinstance(request, aiohttp.web.Request)
        bot: alice.Alice = request.app.bot
        if request.headers.get('Authorization') != bot.config.get('vote_webhook_auth'):
            return aiohttp.web.Response(text='Unauthorized', status=401)
        else:
            webhook: discord.Webhook = await bot.get_webhook_info(bot.config.get('vote_webhook_id'))
            jj = await request.json()
            await webhook.send(f"Recieved vote: {jj}")
            bot.logger.debug(f"Recieved vote: {jj}")
            return aiohttp.web.Response(text="Success")

    bot.add_cog(Home(bot, s_routes))
