from tortoise import Tortoise


async def init():
    await Tortoise.init(
        db_url='',
        modules={'models': ['models']}
    )
