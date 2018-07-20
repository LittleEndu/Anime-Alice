import abc

import aiohttp
import asyncio
import discord
import dateutil.parser
from bs4 import BeautifulSoup as BS
from discord.ext import commands

import helper

ANILIST_ANIME_LINK = "https://anilist.co/anime/%s"
ANILIST_QUERY_URL = 'https://graphql.anilist.co'


class ResponseError(Exception):
    def __init__(self, status, *args, **kwargs):
        self.status = status

    pass


class Medium(metaclass=abc.ABCMeta):
    def __init__(self, anilist_id, name):
        self.anilist_id = anilist_id
        self.name = name

    async def anime(self):
        return NotImplemented

    async def manga(self):
        return NotImplemented

    async def characters(self):
        return NotImplemented

    @staticmethod
    async def via_search(ctx: commands.Context, query: str, adult=False, lucky=False):
        return NotImplemented

    def to_embed(self):
        return NotImplemented


class Anime(Medium):
    def __init__(self, anilist_id, name, **kwargs):
        super().__init__(anilist_id, name)
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

    @staticmethod
    def search_query():
        return """
query ($terms: String) {
  Page(page: 1) {
    pageInfo {
      total
    }
    media(search: $terms, type: ANIME) {
      id
      idMal
      description
      episodes
      title {
        romaji
        english
        native
      }
      popularity
      status
      isAdult
      stats {
        scoreDistribution {
          score
          amount
        }
      }
      startDate {
        year
        month
        day
      }
      endDate {
        year
        month
        day
      }
      coverImage {
        large
      }
    }
  }
}
"""

    @staticmethod
    def id_query(anilist_id: int):
        return """
{
  Page (page:1){
    pageInfo{
      total
    }
    media (id: "%s", type: ANIME){
      id
      idMal
      description
      episodes
      title {
        romaji
        english
        native
      }
      popularity
      status
      isAdult
      stats {
        scoreDistribution {
          score,
          amount
        }
      }
      startDate {year, month, day}
      endDate {year, month, day}
      coverImage {
        large
      }
    }
  }
}
""" % anilist_id

    @staticmethod
    async def via_search(ctx: commands.Context, query: str, adult=False, lucky=False):
        results = []  # Because PyCharm :shrug:
        async with aiohttp.ClientSession() as session:
            async with session.post(url=ANILIST_QUERY_URL,
                                    json={'query': Anime.search_query(),
                                          'variables': {'terms': query}}) as response:
                if response.status == 200:
                    jj = await response.json()
                    results = jj['data']['Page']['media']
                else:
                    raise ResponseError(response.status, await response.text())
        results.sort(key=lambda k: k['popularity'], reverse=True)
        for i in results[:]:
            if i['isAdult'] and not adult:
                results.remove(i)
                continue
            i['description'] = BS(i['description'], "html.parser").text

        if results:
            asking = []
            for i in results:
                under = i['title']['english']
                if under is not None:
                    under = f"*{under}*"
                else:
                    under = ''
                asking.append(f"  {i['title']['romaji']}\n\t{under}")
            if lucky:
                index = 0
            else:
                index = await helper.Asker(ctx, *asking[:9])
            wanted = results[index]
            await ctx.trigger_typing()
            anilist_scores = [0 for i in range(10)]  # InFuture: Add scores from other sites maybe
            for score in wanted['stats']['scoreDistribution']:
                anilist_scores[score['score'] // 10 - 1] = score['amount']
            wanted['alice_score'] = helper.ci_score(anilist_scores)
            start_date = None
            end_date = None
            if all([wanted['startDate'][i] for i in wanted['startDate']]):
                start_date = str(dateutil.parser.parse("{year}-{month}-{day}".format(**wanted['startDate'])).date())
            if all([wanted['endDate'][i] for i in wanted['endDate']]):
                end_date = str(dateutil.parser.parse("{year}-{month}-{day}".format(**wanted['endDate'])).date())

            return Anime(anilist_id=wanted['id'],
                         name=wanted['title']['romaji'],
                         url=ANILIST_ANIME_LINK % wanted['id'],
                         aliases=[i for i in [wanted['title']['english'], wanted['title']['native']] if i],
                         cover_url=wanted['coverImage']['large'],
                         episodes=wanted['episodes'],
                         alice_score=wanted['alice_score'],
                         description=wanted['description'],
                         status=wanted['status'].replace("_", " ").capitalize(),
                         start_date=start_date,
                         end_date=end_date)
        return

    @staticmethod
    async def via_id(ctx: commands.Context, anilist_id: int):
        # TODO: Implement

        to_return = Anime(anilist_id=id, name='name')
        return to_return

    async def anime(self):
        # TODO: Return related anime instead
        return [self]

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
                            value="{}{}".format(
                                self.start_date,
                                " to {}".format(self.end_date) if self.end_date else ""
                            ))

        return embed
