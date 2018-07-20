import asyncio

import asyncpg
import discord

if False:
    import alice



class Database:
    def __init__(self, bot: 'alice.Alice', db_host: str, db_name: str, user_name: str, password: str):
        self.bot = bot
        self.db_host = db_host
        self.db_name = db_name
        self.user_name = user_name
        self.password = password
        self.pool: asyncpg.pool.Pool = None

    async def wait_for_start(self):
        while not self.pool:
            await asyncio.sleep(0)

    async def start(self):
        self.pool = await asyncpg.create_pool(host=self.db_host,
                                              database=self.db_name,
                                              user=self.user_name,
                                              password=self.password)

    async def close(self):
        await self.pool.close()

    async def table_exists(self, table_name: str):
        async with self.pool.acquire() as connection:
            assert isinstance(connection, asyncpg.Connection)
            result = await connection.fetchrow("""
                     SELECT 1
                     FROM   information_schema.tables 
                     WHERE  table_name = $1;
                     """, table_name)
            return result

    async def create_prefixes_table(self):
        async with self.pool.acquire() as connection:
            assert isinstance(connection, asyncpg.Connection)
            await connection.execute("""
            CREATE TABLE IF NOT EXISTS prefixes(
                guild_id BIGINT,
                prefix TEXT,
                UNIQUE (guild_id, prefix)
            );
            """)
            await connection.execute("""
            CREATE INDEX IF NOT EXISTS prefix_index ON prefixes (guild_id);
            """)

    async def count_prefixes(self, guild: discord.Guild):
        if not await self.table_exists('prefixes'):
            return 0
        async with self.pool.acquire() as connection:
            assert isinstance(connection, asyncpg.Connection)
            result = await connection.fetchrow(
                """
                SELECT count(1) FROM prefixes
                WHERE guild_id = $1;
                """, guild.id)
            return result[0]

    async def get_prefixes(self, message: discord.Message):
        if not await self.table_exists('prefixes'):
            return []
        async with self.pool.acquire() as connection:
            assert isinstance(connection, asyncpg.Connection)
            result = await connection.fetch("""
                     SELECT prefix FROM prefixes WHERE guild_id = $1;
                     """, message.guild.id)
            return [i['prefix'] for i in result]

    async def add_prefix(self, guild: discord.Guild, prefix: str):
        async with self.pool.acquire() as connection:
            assert isinstance(connection, asyncpg.Connection)
            await connection.execute("""
            INSERT INTO prefixes (guild_id, prefix)
            VALUES ($1, $2);
            """, *(guild.id, prefix))

    async def remove_prefix(self, guild: discord.Guild, prefix: str):
        async with self.pool.acquire() as connection:
            assert isinstance(connection, asyncpg.Connection)
            await connection.execute("""
            DELETE FROM prefixes
            WHERE guild_id = $1 AND prefix = $2;
            """, *(guild.id, prefix))


def setup(bot: 'alice.Alice'):
    bot.database = Database(bot,
                            bot.config.get('DB_host'),
                            bot.config.get('DB_name'),
                            bot.config.get('DB_user'),
                            bot.config.get('DB_password'))
    bot.loop.run_until_complete(bot.database.start())


def teardown(bot: 'alice.Alice'):
    bot.loop.run_until_complete(bot.database.close())
