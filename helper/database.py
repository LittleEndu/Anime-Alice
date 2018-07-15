import asyncio
import concurrent.futures

import apsw
import discord

import alice


# basically this module should provide consistency
# all functions in here should achieve the same thing, no matter what database is running
# it's here just so I could use some other database (like postgres :shrug:) in future

# region classes

class BaseSQL:
    def __init__(self, sql: str, args: tuple = None):
        self.future = asyncio.Future()
        self.sql = sql
        self.args = args

    async def async_result(self):
        while not self.future.done():
            await asyncio.sleep(0)
        return self.future.result()


class Database:
    def __init__(self, bot: alice.Alice, database_name: str):
        self.running = True
        self.bot = bot
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.connection = apsw.Connection(database_name)
        self.execution_queue = asyncio.Queue()
        self.bot.loop.create_task(self.run_once())

    def insert(self, sql: BaseSQL):
        self.execution_queue.put_nowait(sql)

    def close(self):
        self.running = False

    async def run_once(self):
        base_sql = await self.execution_queue.get()
        if self.running:
            self.bot.loop.create_task(self.run_once())  # run once again.
            # Allows to execute more than one SQL query at the time
        cursor = self.connection.cursor()
        future = self.bot.loop.run_in_executor(self.executor, cursor.execute, base_sql.sql, base_sql.args)
        while not future.done():
            await asyncio.sleep(0)
        try:
            base_sql.future.set_result(list(future.result()))  # Give result
        except Exception as e:
            base_sql.future.set_exception(e)  # There was an SQL error so we should set that as result instead
            # So that commands/other functions can react to that error accordingly


class AsyncExecute:
    def __init__(self, database: Database, sql: str, args: tuple = None):
        self.database = database
        self.sql = BaseSQL(sql, args)

    def __await__(self):
        self.database.insert(self.sql)  # Wait for result
        return self.sql.async_result().__await__()


# endregion


# region functions

async def table_exists(database: Database, table_name: str):
    # returns falsely object when table doesn't exist, otherwise returns truthful object
    result = await AsyncExecute(database, """SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;""",
                                (table_name,))
    return result


# region prefix functions

async def create_prefixes_table(database: Database):
    # Initialises 'prefixes' table
    await AsyncExecute(database, """
        CREATE TABLE IF NOT EXISTS prefixes(
            guild_id BIGINT,
            prefix TEXT,
            unique (guild_id, prefix)
        );
        """)


async def get_prefixes(database: Database, message: discord.Message) -> list:
    # returns list of prefixes that apply to this discord.Message
    table_is_there = await table_exists(database, 'prefixes')
    if table_is_there:
        result = await AsyncExecute(database,
                                    """SELECT prefix FROM prefixes WHERE guild_id = ?;""", (message.guild.id,)
                                    )
        return [i[0] for i in result]
    else:
        return []


async def get_prefix_count(database: Database, guild_id: int):
    # returns the number of prefixes particular guild has
    return await AsyncExecute(database, """
                        SELECT count(1) FROM prefixes
                        WHERE guild_id = ?;
                        """, (guild_id,))


async def set_prefix(database: Database, guild_id: int, prefix: str):
    # inserts prefix into 'prefixes'
    await AsyncExecute(database, """
            INSERT INTO prefixes (guild_id, prefix)
            VALUES (?, ?);
            """, (guild_id, prefix))


async def remove_prefix(database: Database, guild_id: int, prefix: str):
    # removes prefix from 'prefixes'
    await AsyncExecute(database, """
        DELETE FROM prefixes
        WHERE guild_id=? AND prefix=?
        """, (guild_id, prefix))

# endregion

# endregion
