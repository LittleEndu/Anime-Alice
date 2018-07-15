import abc


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
    async def anime(self):
        # TODO: Return related anime instead
        return [self]