import abc
import asyncio
import time

import aiohttp
import dateutil.parser
import discord
from bs4 import BeautifulSoup as BS
from discord.ext import commands

import alice

ANILIST_QUERY_URL = 'https://graphql.anilist.co'


class ResponseError(Exception):
    def __init__(self, status, *args, **kwargs):
        self.status = status
    # end class


class NSFWBreach(Exception):
    pass


def merge(a, b, path=None):
    "merges b into a"
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


class Otaku:
    # region Helpers
    @staticmethod
    async def get_anilist_results(graphql: dict, adult=False, result_type='media'):
        results = []
        async with aiohttp.ClientSession() as session:
            async with session.post(url=ANILIST_QUERY_URL,
                                    json=graphql) as response:
                if response.status == 200:
                    jj = await response.json()
                    results = jj['data']['Page'][result_type]
                else:
                    raise ResponseError(response.status, await response.text())
        try:
            for i in results[:]:
                if i['isAdult'] and not adult:
                    results.remove(i)
        except:
            pass
        try:
            results.sort(key=lambda k: k['popularity'], reverse=True)
        except:
            pass
        return results

    @staticmethod
    async def get_more_anilist_info(graphql: dict, previous_info: dict,
                                    score_func=lambda l: sum(l) / float(len(l)), result_type='Media'):
        result = dict()
        async with aiohttp.ClientSession() as session:
            async with session.post(url=ANILIST_QUERY_URL,
                                    json=graphql) as response:
                if response.status == 200:
                    jj = await response.json()
                    result = merge(previous_info, jj['data'][result_type])
                else:
                    raise ResponseError(response.status, await response.text())
        try:
            # Escape html that's in description
            # lxml seems to be the only thing that works
            result['description'] = BS(result['description'], "lxml").text
        except:
            pass
        try:
            anilist_scores = [0 for i in range(10)]
            for score in result['stats']['scoreDistribution']:
                anilist_scores[score['score'] // 10 - 1] = score['amount']
            result['alice_score'] = score_func(anilist_scores)
        except:
            pass
        start_date = None
        end_date = None
        try:
            if all([result['startDate'][i] for i in result['startDate']]):
                start_date = str(dateutil.parser.parse("{year}-{month}-{day}".format(**result['startDate'])).date())
            if all([result['endDate'][i] for i in result['endDate']]):
                end_date = str(dateutil.parser.parse("{year}-{month}-{day}".format(**result['endDate'])).date())
        except:
            pass
        result['formatted_start_date'] = start_date
        result['formatted_end_date'] = end_date
        return result

    @staticmethod
    def clean_descriptions(description: str):
        while description.find("~!") != -1:
            start = description.find('~!')
            end = description.find('!~')
            spoiler = description[start:end + 2]
            description = description.replace(spoiler, "")
        while description.find('\n') < 30:
            if description.find("\n") == -1:
                break
            end = description.find("\n")
            description = description[end + 1:]
        return description

    @staticmethod
    def join_names(*names):
        return ", ".join(i for i in names if i)

    class GraphQLKey:
        def __init__(self, *, name, signature=None, keys: tuple = None):
            self.name = name
            self.signature = signature or ""
            if keys:
                for key in keys:
                    if not isinstance(key, Otaku.GraphQLKey):
                        raise TypeError
            self.keys = keys or tuple()

        def __eq__(self, other):
            if isinstance(other, Otaku.GraphQLKey):
                return str(self) == str(other)
            if isinstance(other, str):
                return self.name == other
            return NotImplemented

        def __getitem__(self, item) -> 'Otaku.GraphQLKey':
            if isinstance(item, str):
                for key in self.keys:
                    if key.name == item:
                        return key
                new_key = Otaku.GraphQLKey(name=item)
                self.keys += (new_key,)
                return new_key
            elif isinstance(item, Otaku.GraphQLKey):
                for key in self.keys:
                    if key.name == item.name:
                        return key
                self.keys += (item,)
                return item
            raise TypeError

        def __str__(self):
            after = ""
            if self.signature:
                after += f"({self.signature})"
            if self.keys:
                after += "{" + " ".join(map(str, self.keys)) + "}"
            return f"{self.name}{after}"

        def __add__(self, other):
            if isinstance(other, dict):
                other = Otaku.GraphQLKey.from_dict(other, name=self.name)
            if not isinstance(other, Otaku.GraphQLKey):
                raise TypeError(f"unsupported operand type(s) for +: 'GraphQLKey' and '{type(other)}'")
            if not self.name == other.name:
                raise ValueError('names must equal')
            return Otaku.GraphQLKey.from_dict(merge(self.to_dict(), other.to_dict()))

        def __sub__(self, other):
            if isinstance(other, dict):
                other = Otaku.GraphQLKey.from_dict(other, name=self.name)
            if not isinstance(other, Otaku.GraphQLKey):
                raise TypeError(f"unsupported operand type(s) for -: 'GraphQLKey' and '{type(other)}'")
            if not self.name == other.name:
                raise ValueError('names must equal')
            for key in other.keys:
                my_keys = tuple()
                for i in self.keys:
                    # don't add it back when it's the same thing
                    if i == key:
                        continue
                    # check if it has children and we could subtract those
                    if i.name == key.name and len(key.keys) > 0:
                        result = i - key
                        if len(result.keys) == 0:
                            continue
                        my_keys += (result,)
                    else:
                        my_keys += (i,)

                self.keys = my_keys
            return self

        @staticmethod
        def from_dict(dictionary: dict, *, name=None, signature=None):
            if name is None:
                if len(dictionary) > 1:
                    raise ValueError('must provide name or have a dict with one key')
                name = list(dictionary.keys())[0]
                if not isinstance(name, str):
                    raise TypeError('must provide name or key in dict must be str')
                if isinstance(dictionary[name], tuple):
                    rv = Otaku.GraphQLKey(name=name, signature=dictionary[name][0])
                    dictionary = dictionary[name][1]
                else:
                    rv = Otaku.GraphQLKey(name=name)
                    dictionary = dictionary[name]
            else:
                rv = Otaku.GraphQLKey(name=name, signature=signature)
            for key in dictionary:
                assert isinstance(key, str)
                if isinstance(dictionary[key], list):
                    dictionary[key] = dictionary[key][0]
                if isinstance(dictionary[key], dict):
                    _ = rv[Otaku.GraphQLKey.from_dict(dictionary[key], name=key)]
                elif isinstance(dictionary[key], tuple):
                    _ = rv[Otaku.GraphQLKey.from_dict(dictionary[key][1], name=key, signature=dictionary[key][0])]
                else:
                    _ = rv[key]
            return rv

        def to_dict(self):
            rv = dict()
            if self.signature:
                dd = dict()
                for key_dict in [key.to_dict() for key in self.keys]:
                    dd = {**dd, **key_dict}
                rv[self.name] = (self.signature, dd if dd else '_')
            else:
                dd = dict()
                for key_dict in [key.to_dict() for key in self.keys]:
                    dd = {**dd, **key_dict}
                rv[self.name] = dd if dd else '_'
            return rv

    class Medium:
        def __init__(self, some_id, name, is_nsfw=False):
            self.id = some_id
            self.name = name
            self.is_nsfw = is_nsfw
            self.instance_created_at = time.time()

        async def related(self, adult=False, lucky=False):
            return NotImplemented

        async def anime(self, adult=False, lucky=False):
            return NotImplemented

        async def manga(self, adult=False, lucky=False):
            return NotImplemented

        async def character(self, adult=False, lucky=False):
            return NotImplemented

        @staticmethod
        async def via_search(ctx: commands.Context, query: str, adult=False, lucky=False):
            return NotImplemented

        def to_embed(self):
            return NotImplemented
        # end class

    class Anime(Medium):
        def __init__(self, anilist_id, name, **kwargs):
            super().__init__(anilist_id, name, kwargs.get('is_nsfw', False))
            self.url = kwargs.get('url')
            self.romaji_name = kwargs.get('romaji_name', name)
            self.aliases = kwargs.get('aliases', [])
            self.cover_url = kwargs.get('cover_url', 'https://puu.sh/vPxRa/6f563946ec.png')
            self.episodes = kwargs.get('episodes', 'Unknown') or 'Unknown'
            self.alice_score = kwargs.get('alice_score', 'N/A') or 'N/A'
            self.description = kwargs.get('description', 'N/A') or 'N/A'
            self.status = kwargs.get('status', 'N/A') or 'N/A'
            self.start_date = kwargs.get('start_date')
            self.end_date = kwargs.get('end_date')
            self.kwargs = kwargs

        async def anime(self, adult=False, lucky=False):
            if not adult and self.is_nsfw:
                raise NSFWBreach
            return self

        @staticmethod
        def search_query():
            # You can use graph_ql_builder.py to prettify it
            # @formatter:off
            return Otaku.GraphQLKey.from_dict(
                {'query': ('$terms: String', {'Page': ('page: 1', {'media': ('search: $terms, type: ANIME', {'id': '_', 'isAdult': '_', 'title': {'romaji': '_', 'english': '_'}, 'popularity': '_'})})})}
            )
            # @formatter:on

        @staticmethod
        def populate_query():
            # You can use graph_ql_builder.py to prettify it
            # @formatter:off
            return Otaku.GraphQLKey.from_dict(
                {'query': ('$id: Int', {'Media': ('id: $id, type: ANIME', {'id': '_', 'isAdult': '_', 'siteUrl': '_', 'description': '_', 'episodes': '_', 'title': {'romaji': '_', 'english': '_', 'native': '_'}, 'status': '_', 'stats': {'scoreDistribution': {'score': '_', 'amount': '_'}}, 'startDate': {'year': '_', 'month': '_', 'day': '_'}, 'endDate': {'year': '_', 'month': '_', 'day': '_'}, 'coverImage': {'large': '_'}})})}
            )
            # @formatter:on

        @staticmethod
        async def via_search(ctx: commands.Context, query: str, adult=False, lucky=False):
            # Searches Anilist for that query
            # Returns Anime()

            graph_ql_key = Otaku.Anime.search_query()
            graph_ql = {'query': str(graph_ql_key),
                        'variables': {'terms': query}}
            results = await Otaku.get_anilist_results(graph_ql, adult)

            if results:
                if lucky:
                    index = 0  # Lucky search always returns most popular
                else:
                    asking = []
                    for i in results:
                        under = i['title']['english']
                        if under is not None:
                            under = f"*{under}*"
                        else:
                            under = ''
                        asking.append(f"  **{i['title']['romaji']}**\n\t{under}")
                    # Ask the user what anime they meant
                    index = await ctx.bot.helper.Asker(ctx, *asking[:9])
                return await Otaku.Anime.from_results(ctx, results[index])

        @staticmethod
        async def from_results(ctx, result):
            await ctx.trigger_typing()
            graph_ql_key = Otaku.Anime.populate_query()
            media = graph_ql_key['Media']
            media -= result
            graph_ql = {'query': str(graph_ql_key),
                        'variables': {'id': result['id']}}
            result = await Otaku.get_more_anilist_info(graph_ql, result, ctx.bot.helper.ci_score)
            return Otaku.Anime(anilist_id=result['id'],
                               name=result['title']['romaji'],
                               url=result['siteUrl'],
                               aliases=[i for i in [result['title']['english'], result['title']['native']] if i],
                               cover_url=result['coverImage']['large'],
                               episodes=result['episodes'],
                               alice_score=result['alice_score'],
                               description=result['description'],
                               status=result['status'].replace("_", " ").capitalize(),
                               start_date=result['formatted_start_date'],
                               end_date=result['formatted_end_date'],
                               is_nsfw=result['isAdult'])

        def to_embed(self):
            embed = discord.Embed(description="\n".join(self.aliases) if self.aliases else None)
            embed.set_author(name=self.romaji_name, url=self.url)
            embed.set_thumbnail(url=self.cover_url)
            embed.add_field(name="Episodes", value=self.episodes)
            embed.add_field(name="Score", value=str(self.alice_score)[:4] if self.alice_score else "N/A")
            text = self.description
            if len(text) > 300:
                text = " ".join(text[:300].split()[:-1])
                embed.add_field(name="Synopsis", value=text + " ...", inline=False)
            else:
                embed.add_field(name="Synopsis", value=text, inline=False)
            embed.add_field(name="Status", value=self.status)
            if self.start_date:
                embed.add_field(name=f"Airing date{'s' if self.end_date else ''}",
                                value="{}{}{}".format(
                                    "From " if not self.end_date else "",
                                    self.start_date,
                                    " to {}".format(self.end_date) if self.end_date else ""
                                ))
            embed.add_field(name='\u200b', value=f"[Anilist]({self.url})", inline=False)
            embed.set_footer(text='Anime')

            return embed
        # end class

    class Manga(Medium):
        def __init__(self, anilist_id, name, **kwargs):
            super().__init__(anilist_id, name, kwargs.get('is_nsfw', False))
            self.url = kwargs.get('url')
            self.romaji_name = kwargs.get('romaji_name', name)
            self.aliases = kwargs.get('aliases', [])
            self.cover_url = kwargs.get('cover_url', 'https://puu.sh/vPxRa/6f563946ec.png')
            self.chapters = kwargs.get('chapters', 'Unknown') or 'Unknown'
            self.alice_score = kwargs.get('alice_score', 'N/A') or 'N/A'
            self.description = kwargs.get('description', 'N/A') or 'N/A'
            self.status = kwargs.get('status', 'N/A') or 'N/A'
            self.start_date = kwargs.get('start_date')
            self.end_date = kwargs.get('end_date')
            self.kwargs = kwargs

        async def manga(self, adult=False, lucky=False):
            if not adult and self.is_nsfw:
                raise NSFWBreach
            return self

        @staticmethod
        def search_query():
            # @formatter:off
            return Otaku.GraphQLKey.from_dict({'query': ('$terms: String', {'Page': {'media': ('search: $terms, format_in: [MANGA, ONE_SHOT]', {'id': '_', 'isAdult': '_', 'title': {'romaji': '_', 'english': '_'}, 'format': '_', 'popularity': '_'})}})})
            # @formatter:on

        @staticmethod
        def populate_query():
            # @formatter:off
            return Otaku.GraphQLKey.from_dict({'query': ('$id: Int', {'Media': ('id: $id, format_in: [MANGA, ONE_SHOT]', {'id': '_', 'siteUrl': '_', 'description': '_', 'chapters': '_', 'isAdult': '_', 'title': {'romaji': '_', 'english': '_', 'native': '_'}, 'status': '_', 'stats': {'scoreDistribution': {'score': '_', 'amount': '_'}}, 'startDate': {'year': '_', 'month': '_', 'day': '_'}, 'endDate': {'year': '_', 'month': '_', 'day': '_'}, 'coverImage': {'large': '_'}})})})
            # @formatter:on

        @staticmethod
        async def via_search(ctx: commands.Context, query: str, adult=False, lucky=False):
            # Searches Anilist for that query
            # Returns Manga()

            graph_ql_key = Otaku.Manga.search_query()
            graph_ql = {'query': str(graph_ql_key),
                        'variables': {'terms': query}}

            results = await Otaku.get_anilist_results(graph_ql, adult)
            if results:
                if lucky:
                    index = 0  # Lucky search always returns most popular
                else:
                    asking = []
                    for i in results:
                        under = i['title']['english']
                        if under is not None:
                            under = f"*{under}*"
                        else:
                            under = ''
                        if i['format'] == 'ONE_SHOT':
                            under += " __One shot__"
                        asking.append(f"  **{i['title']['romaji']}**\n\t{under}")
                    # Ask the user what anime they meant
                    index = await ctx.bot.helper.Asker(ctx, *asking[:9])

                wanted = results[index]

                # Query Anilist for all information about that anime

                return await Otaku.Manga.from_results(ctx, wanted)

        @staticmethod
        async def from_results(ctx, result):
            await ctx.trigger_typing()
            graph_ql_key = Otaku.Manga.populate_query()
            media = graph_ql_key['Media']
            media -= result
            graph_ql = {'query': str(graph_ql_key),
                        'variables': {'id': result['id']}}

            result = await Otaku.get_more_anilist_info(graph_ql,
                                                       result,
                                                       ctx.bot.helper.ci_score)
            return Otaku.Manga(anilist_id=result['id'],
                               name=result['title']['romaji'],
                               url=result['siteUrl'],
                               aliases=[i for i in [result['title']['english'], result['title']['native']] if i],
                               cover_url=result['coverImage']['large'],
                               chapters=result['chapters'],
                               alice_score=result['alice_score'],
                               description=result['description'],
                               status=result['status'].replace("_", " ").capitalize(),
                               start_date=result['formatted_start_date'],
                               end_date=result['formatted_end_date'],
                               is_nsfw=result['isAdult'])

        def to_embed(self):
            embed = discord.Embed(description="\n".join(self.aliases) if self.aliases else None)
            embed.set_author(name=self.romaji_name, url=self.url)
            embed.set_thumbnail(url=self.cover_url)
            embed.add_field(name="Chapters", value=self.chapters)
            embed.add_field(name="Score", value=str(self.alice_score)[:4] if self.alice_score else "N/A")
            text = self.description
            if len(text) > 300:
                text = " ".join(text[:300].split()[:-1])
                embed.add_field(name="Synopsis", value=text + " ...", inline=False)
            else:
                embed.add_field(name="Synopsis", value=text, inline=False)
            embed.add_field(name="Status", value=self.status)
            if self.start_date:
                embed.add_field(name=f"Releasing date{'s' if self.end_date else ''}",
                                value="{}{}{}".format(
                                    "From " if not self.end_date else "",
                                    self.start_date,
                                    " to {}".format(self.end_date) if self.end_date else ""
                                ))
            embed.add_field(name='\u200b', value=f"[Anilist]({self.url})", inline=False)
            embed.set_footer(text='Manga')

            return embed
        # end class

    class Character(Medium):
        def __init__(self, anilist_id, name, adult, **kwargs):
            super().__init__(anilist_id,
                             name=name,
                             is_nsfw=adult)
            self.url = kwargs.get('url')
            self.native_name = kwargs.get('native_name')
            self.alternative_names = kwargs.get('alternative_names')
            self.description = kwargs.get('description')
            self.cover_url = kwargs.get('cover_url', 'https://puu.sh/vPxRa/6f563946ec.png')

        async def character(self, adult=False, lucky=False):
            if not adult and self.is_nsfw:
                raise NSFWBreach
            return self

        @staticmethod
        def search_query():
            # @formatter:off
            return Otaku.GraphQLKey.from_dict({'query': ('$terms: String', {'Page': ('page: 1, perPage: 500', {'characters': ('search: $terms', {'id': '_', 'name': {'first': '_', 'last': '_'}, 'media': {'nodes': {'id': '_', 'isAdult': '_', 'title': {'romaji': '_'}, 'popularity': '_'}}})})})})
            # @ formatter:on

        @staticmethod
        def populate_query():
            # @formatter:off
            return Otaku.GraphQLKey.from_dict({'query': ('$id: Int', {'Character': ('id: $id', {'description': '_', 'name': {'native': '_', 'alternative': '_'}, 'siteUrl': '_', 'image': {'large': '_'}})})})
            # @formatter:on

        @staticmethod
        async def via_search(ctx: commands.Context, query: str, adult=False, lucky=False):
            # Searches Anilist for that query
            # Returns Character()

            graph_ql_key = Otaku.Character.search_query()
            graph_ql = {'query': str(graph_ql_key),
                        'variables': {'terms': query}}
            results = await Otaku.get_anilist_results(graph_ql,
                                                      adult,
                                                      result_type='characters')
            if results:
                for i in results:
                    medias = sorted(i['media']['nodes'], key=lambda a: a['popularity'], reverse=True)
                    i['media']['nodes'] = medias
                    if not medias:
                        i['popularity'] = 0
                        continue
                    i['popularity'] = medias[0]['popularity']
                results.sort(key=lambda a: a['popularity'], reverse=True)

                asking = []
                for i in results[:]:
                    medias = i['media']['nodes']
                    i['isAdult'] = False
                    if not medias or medias[0]['isAdult']:
                        if not medias or not adult:
                            results.remove(i)  # Remove non-existings (and hentai)
                            continue
                        elif medias:
                            i['isAdult'] = True  # Set hentai to true if we searching for it
                    under = f"*From {medias[0]['title']['romaji']}*"
                    i['full_name'] = Otaku.join_names(i['name']['first'], i['name']['last'])
                    asking.append(f"  **{i['full_name']}**\n\t{under}")

                index = 0  # Lucky search always returns most popular
                if not lucky:
                    # Ask the user what anime they meant
                    index = await ctx.bot.helper.Asker(ctx, *asking)

                wanted = results[index]
                return await Otaku.Character.from_results(ctx, wanted)

        @staticmethod
        async def from_results(ctx, result, is_adult=None, full_name=None):
            graph_ql_key = Otaku.Character.populate_query()
            try:
                result['isAdult']
            except KeyError:
                if is_adult:
                    result['isAdult'] = is_adult
                else:
                    raise
            try:
                result['full_name']
            except KeyError:
                if full_name:
                    result['full_name'] = full_name
                else:
                    name = graph_ql_key['Character']['name']
                    name += {'name': {'first': '_', 'last': '_'}}
            chara = graph_ql_key['Character']
            chara -= result

            graph_ql = {'query': str(graph_ql_key),
                        'variables': {'id': result['id']}}
            await ctx.trigger_typing()
            result = await Otaku.get_more_anilist_info(graph_ql, result, result_type='Character')
            result['description'] = Otaku.clean_descriptions(result['description'])

            return Otaku.Character(anilist_id=result['id'],
                                   name=result.get('full_name',
                                                   Otaku.join_names(result['name']['first'], result['name']['last'])),
                                   native_name=result['name']['native'],
                                   alternative_names=result['name']['alternative'],
                                   adult=result['isAdult'],
                                   description=result['description'],
                                   url=result['siteUrl'],
                                   cover_url=result['image']['large'])

        def to_embed(self):
            embed = discord.Embed(description=f"{', '.join(self.alternative_names)}\n{self.native_name}")
            embed.set_author(name=self.name, url=self.url)
            embed.set_thumbnail(url=self.cover_url)
            text = self.description
            if len(text) > 300:
                text = " ".join(text[:300].split()[:-1])
                embed.add_field(name="Description", value=text + " ...", inline=False)
            else:
                embed.add_field(name="Description", value=text, inline=False)
            embed.add_field(name='\u200b', value=f"[Anilist]({self.url})", inline=False)
            embed.set_footer(text='Character')
            return embed
        # end class

    class CommandCopyHelper:
        def __init__(self, callback, aliases):
            self.callback = callback
            self.aliases = aliases

        def new_command(self):
            return commands.command(aliases=self.aliases)(self.callback)

    # This is where the actual cog starts
    # Anything else before are just helpers
    # endregion

    # region Cog

    mediums = {'anime': Anime, 'hentai': Anime, 'manga': Manga, 'character': Character}
    for key in list(mediums.keys()):
        mediums[f'{key}s'] = mediums[key]

    def __init__(self, bot: alice.Alice):
        self.bot = bot
        self._last_medium = dict()
        find_command = Otaku.CommandCopyHelper(self.find, ['?', 'search'])
        lucky_command = Otaku.CommandCopyHelper(self.lucky, ['!', 'luckysearch'])
        for g in [self.anime, self.manga, self.character]:
            for s in [find_command, lucky_command]:
                g.add_command(s.new_command())
        self.cleanup_task = self.bot.loop.create_task(self.cleanuper())

    def __unload(self):
        self.cleanup_task.cancel()

    async def cleanuper(self):
        try:
            while True:
                for k in list(self._last_medium.keys()):
                    if self._last_medium[k].age < time.time() - 600:
                        del self._last_medium
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def last_medium_caller(self, ctx: commands.Context, parent_name: str, lucky=False):
        medium = self._last_medium.get(ctx.author.id)
        if not medium:
            await ctx.send("You haven't used any search commands yet")
            return
        func = getattr(medium, parent_name)
        try:
            new_medium = await func(lucky=lucky)
        except asyncio.TimeoutError:
            return
        except NSFWBreach:
            await ctx.send(f"Can't show that {parent_name} here. It's NSFW")
            return
        if new_medium is NotImplemented:
            await ctx.send(f"I'm sorry. I can't do that yet.\n"
                           f"{medium.__class__.__name__} doesn't implement ``{ctx.prefix}{parent_name}`` yet.")
        elif new_medium is None:
            await ctx.send('No results...')
        else:
            embed = new_medium.to_embed()
            await ctx.send(embed=embed)
            self._last_medium[ctx.author.id] = new_medium

    @commands.command(name='search', aliases=['find', '?'])
    @commands.bot_has_permissions(embed_links=True)
    async def _search(self, ctx, medium_name: str, *, query: str = None):
        """Alias for when you type search before the medium you want to search for"""
        if not medium_name in Otaku.mediums:
            raise commands.UserInputError(f'{medium_name.capitalize()} is not something I can search for')
        if query is None:
            query = (await self.bot.helper.AdditionalInfo(ctx, *('What do you want to search for?',)))[0]
        medium_name = medium_name.lower()
        await self.find_helper(ctx, medium_name, query, False)

    @commands.command(name='lucky', aliases=['luckysearch', '!'])
    @commands.bot_has_permissions(embed_links=True)
    async def _lucky(self, ctx, medium_name: str, *, query: str = None):
        """Alias for when you type lucky before the medium you want to lucky search"""
        if not medium_name in Otaku.mediums:
            raise commands.UserInputError(f'{medium_name.capitalize()} is not something I can search for')
        if query is None:
            query = (await self.bot.helper.AdditionalInfo(ctx, *('What do you want to search for?',)))[0]
        medium_name = medium_name.lower()
        await self.find_helper(ctx, medium_name, query, True)

    @commands.group(aliases=['hentai', 'hentais', 'animes'],
                    brief="Used for anime lookup. Use ``help anime`` command for more info")
    @commands.bot_has_permissions(embed_links=True)
    async def anime(self, ctx: commands.Context):
        """
* ``!anime search <query>`` - Searches Anilist for anime. ``search`` can be replaced with ``?``
* ``!anime lucky <query>`` - Searches Anilist for anime. Automatically picks the most popular. ``lucky`` can be replaced with ``!``
    * ``!anime`` - Shows the last anime you looked up
    * ``!manga`` - *Currently doesn't work*
    * ``!character`` - *Currently doesn't work*
    """
        if ctx.invoked_with.startswith('hentai') and not ctx.channel.nsfw:
            await ctx.send("Can't search hentai in here")
        if ctx.invoked_subcommand is None:
            if ctx.message.content != f"{ctx.prefix}{ctx.invoked_with}":
                await ctx.send("This is not how you use this command")
                return
            await self.last_medium_caller(ctx, 'anime', False)
            return

    @commands.group(aliases=['mangas'],
                    brief="Used for manga lookup. Use ``help manga`` command for more info")
    @commands.bot_has_permissions(embed_links=True)
    async def manga(self, ctx: commands.Context):
        """
* ``!manga search <query>`` - Searches Anilist for manga. ``search`` can be replaced with ``?``
* ``!manga lucky <query>`` - Searches Anilist for manga. Automatically picks the most popular. ``lucky`` can be replaced with ``!``
    * ``!anime`` - *Currently doesn't work*
    * ``!manga`` - Shows the last manga you looked up
    * ``!character`` - *Currently doesn't work*
    """
        if ctx.invoked_subcommand is None:
            if ctx.message.content != f"{ctx.prefix}{ctx.invoked_with}":
                await ctx.send("This is not how you use this command")
                return
            await self.last_medium_caller(ctx, 'manga', False)
            return

    @commands.group(aliases=['characters'],
                    brief="Used for character lookup. Use ``help character`` command for more info")
    @commands.bot_has_permissions(embed_links=True)
    async def character(self, ctx: commands.Context):
        """
* ``!character search <query>`` - Searches Anilist for characters. ``search`` can be replaced with ``?``
* ``!character lucky <query>`` - Searches Anilist for characters. Automatically picks the character with most popular anime/manga. ``lucky`` can be replaced with ``!``
    * ``!anime`` - *Currently doesn't work*
    * ``!manga`` - *Currently doesn't work*
    * ``!character`` - Shows the last result
    """
        if ctx.invoked_subcommand is None:
            if ctx.message.content != f"{ctx.prefix}{ctx.invoked_with}":
                await ctx.send("This is not how you use this command")
                return
            await self.last_medium_caller(ctx, 'character', False)
            return

    # medium.command()
    async def lucky(self, ctx: commands.Context, *, query: str = None):
        if query is None:
            query = (await self.bot.helper.AdditionalInfo(ctx, *('What do you want to search for?',)))[0]
        await self.find_helper(ctx, ctx.command.parent.name, query, True)

    # medium.command()
    async def find(self, ctx: commands.Context, *, query: str = None):
        if query is None:
            query = (await self.bot.helper.AdditionalInfo(ctx, *('What do you want to search for?',)))[0]
        await self.find_helper(ctx, ctx.command.parent.name, query, False)

    async def find_helper(self, ctx, medium_name, query, lucky):
        cls = Otaku.mediums.get(medium_name)
        assert issubclass(cls, Otaku.Medium)
        await ctx.trigger_typing()
        nsfw = isinstance(ctx.channel, discord.DMChannel) or ctx.channel.nsfw
        try:
            medium = await cls.via_search(ctx, query, adult=nsfw, lucky=lucky)
        except asyncio.TimeoutError:
            return
        if medium is NotImplemented:
            await ctx.send("I'm sorry. I can't do that yet.")
        elif medium is None:
            await ctx.send('No results...')
        else:
            embed = medium.to_embed()
            await ctx.send(embed=embed)
            self._last_medium[ctx.author.id] = medium
    # endregion
    # end class


def setup(bot):
    bot.add_cog(Otaku(bot))
