import abc
import helper

import discord
from discord.ext import commands


class Medium(metaclass=abc.ABCMeta):
    def __init__(self, anilist_id, name):
        self.anilist_id = anilist_id
        self.name = name

    async def anime(self):
        raise NotImplemented

    async def manga(self):
        raise NotImplemented

    async def characters(self):
        raise NotImplemented


class Anime(Medium):
    def __init__(self, anilist_id, name, **kwargs):
        super().__init__(anilist_id, name)
        self.url = kwargs.get('url')
        self.romaji_name = kwargs.get('romaji_name')
        self.aliases = kwargs.get('aliases', [])
        self.cover_url = kwargs.get('cover_url', 'https://puu.sh/vPxRa/6f563946ec.png')
        self.episodes = kwargs.get('episodes', 'Unknown')
        self.alice_score = kwargs.get('alice_score', None)
        self.description = kwargs.get('description')
        self.status = kwargs.get('status')
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')
        self.kwargs = kwargs

    @staticmethod
    def search_query(query):
        return """
{
  Page (page:1){
    pageInfo{
      total
    }
    media (search: "%s", type: ANIME){
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
""" % query

    @staticmethod
    async def via_query(ctx: commands.Context, query: str):
        # TODO: Implement
        pass

    @staticmethod
    async def via_api(anilist_id: int):
        # TODO: Implement
        to_return = Anime(anilist_id=id, name='name')
        return to_return

    async def via_database(self):
        # TODO: Implement
        pass

    async def anime(self):
        # TODO: Return related anime instead
        return [self]

    async def to_embed(self):
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
        embed.add_field(name="Status", value=self.status.replace("_", " ").capitalize())
        if self.start_date:
            embed.add_field(name=f"Airing date{'s' if self.end_date else ''}",
                            value="{}{}".format(
                                self.start_date,
                                " to {}".format(self.end_date) if self.end_date else ""
                            ))

        return embed
