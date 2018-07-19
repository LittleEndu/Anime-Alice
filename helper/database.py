import aiohttp
import discord

owner = discord.role


# basically this module should provide consistency
# all functions in here should achieve the same thing, no matter what database is running
# it's here just so I could use some other database (like postgres :shrug:) in future


class UnexpectedResponse(Exception):
    def __init__(self, response, status):
        self.response = response
        self.status = status


async def deal_with_response(response):
    jj = await response.json()
    if response.status == 200:
        return jj
    else:
        raise UnexpectedResponse(jj, response.status)


async def create_prefixes_table(db_host: str, session: aiohttp.ClientSession):
    async with session.get(f'{db_host}/db/createPrefixesTable') as response:
        return await deal_with_response(response)


async def get_prefixes(db_host: str, session: aiohttp.ClientSession, message: discord.Message):
    async with session.get(f'{db_host}/db/getPrefixes/{message.guild.id}') as response:
        return await deal_with_response(response)


async def set_prefix(db_host: str, session: aiohttp.ClientSession, guild: discord.Guild, prefix: str):
    async with session.post(f'{db_host}/db/setPrefix', data={'guild_id': guild.id, 'prefix': prefix}) as response:
        return await deal_with_response(response)


async def remove_prefix(db_host: str, session: aiohttp.ClientSession, guild: discord.Guild, prefix: str):
    async with session.delete(f'{db_host}/db/removePrefix', data={'guild_id': guild.id, 'prefix': prefix}) as response:
        return await deal_with_response(response)


async def count_prefix(db_host: str, session: aiohttp.ClientSession, guild: discord.Guild):
    async with session.get(f'{db_host}/db/countPrefix/{guild.id}') as response:
        return await deal_with_response(response)
