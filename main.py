import json
import traceback
from http.cookies import SimpleCookie
import discord
import asyncio
import platform
import os
from aiohttp import ClientSession
from discord.ext import commands

TOKEN = ""
CLIENT_ID = 0
GUILD = 0
headers = {
    'sec-ch-ua': '" Not;A Brand";v="99", "Microsoft Edge";v="103", "Chromium";v="103"',
    'DNT': '1',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/103.0.5060.114 Safari/537.36 Edg/103.0.1264.62",
    'X-API-SOURCE': 'pc',
    'X-Shopee-Language': 'en',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Content-Type': 'application/json',
}


class ShopeeBot(commands.Bot):
    def __init__(
            self,
            http_session: ClientSession,
            extension: str,
            **kwargs
    ):
        intents = discord.Intents.default()
        super().__init__(intents = intents, command_prefix = '-', **kwargs)
        self.client_id: str = CLIENT_ID
        self.http_session = http_session
        self.extension = extension

    async def setup_hook(self) -> None:
        guild = discord.Object(GUILD)
        try:
            for extension in self.extension:
                await self.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {self.extension}.')
            traceback.print_exc()
        self.tree.copy_global_to(guild = guild)
        await self.tree.sync(guild = guild)

    async def on_ready(self):
        print("-------------------")
        print(f'Logged in as {self.user}')
        print(f"Python version: {platform.python_version()}")
        print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        print("-------------------")


def load_cookies():
    try:
        with open("shopee.cookies", "r") as f:
            cookie = json.load(f)
        if type(cookie) != dict:
            os.remove("shopee.cookies")
            raise FileNotFoundError
    except (FileNotFoundError):
        tmp = SimpleCookie()
        tmp.load(input("Enter account cookies: "))
        cookie = {k: v.value for k, v in tmp.items()}
        with open("shopee.cookies", "w+") as f:
            json.dump(cookie, f, ensure_ascii = False, indent = 4)
    finally:
        return cookie


async def main():
    initial_extension = ['shopee']
    async with ClientSession(headers = headers, cookies = load_cookies()) as http_session:
        async with ShopeeBot(http_session, initial_extension) as bot:
            await bot.start(TOKEN)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    asyncio.run(main())