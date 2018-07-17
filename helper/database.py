import json

import aiohttp
import discord

owner = discord.role

# basically this module should provide consistency
# all functions in here should achieve the same thing, no matter what database is running
# it's here just so I could use some other database (like postgres :shrug:) in future

DB_HOST = 'http://localhost'


class UnexpectedResponse(Exception):
    def __init__(self, response):
        self.response = response


async def deal_with_response(response):
    jj = json.loads(await response.text())
    if response.status == 200:
        return jj
    else:
        raise UnexpectedResponse(jj)


async def get_prefixes(session: aiohttp.ClientSession, message: discord.Message):
    async with session.get(f'{DB_HOST}/db/getPrefixes/{message.guild.id}') as response:
        return await deal_with_response(response)


async def set_prefix(session: aiohttp.ClientSession, guild: discord.Guild, prefix: str):
    async with session.post(f'{DB_HOST}/db/setPrefix', data={'guild_id': guild.id, 'prefix': prefix}) as response:
        return await deal_with_response(response)


async def remove_prefix(session: aiohttp.ClientSession, guild: discord.Guild, prefix: str):
    async with session.delete(f'{DB_HOST}/db/removePrefix', data={'guild_id': guild.id, 'prefix': prefix}) as response:
        return await deal_with_response(response)


async def count_prefix(session: aiohttp.ClientSession, guild: discord.Guild):
    async with session.get(f'{DB_HOST}/db/countPrefix/{guild.id}') as response:
        return await deal_with_response(response)
