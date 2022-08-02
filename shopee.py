import json
import traceback
from typing import Optional
import discord
from discord import app_commands
from main import ShopeeBot
from discord.ext import tasks, commands
import re


FINGERPRINT = "5oRernPMG5BMW4IUQ2v7+A==|uJiXshjCcaA/ZccGzJrWdJCxYcyXjfFYO3EYXWRVlvGqqpQStG/px6EuFz9wFzJwojKGRn7cDwm5" \
              "IpGY5ccWTSdgzA==|V44Ci64ArTNC2zsG|05|3"


class Shopee(commands.Cog):
    def __init__(self, bot: ShopeeBot):
        self.bot: ShopeeBot = bot
        self.session = bot.http_session

    # Triggered when Cog gets loaded
    async def cog_load(self):
        async with self.session.get('https://shopee.com.my/api/v2/user/profile/get/') as response:
            result = await response.json()
            if result['error'] == 19:
                print("Login failed!")
                return
            print("Logged in as " + result['data']['display_name'] + "!")

    # Triggered after Cog gets unloaded
    async def cog_unload(self) -> None:
        self.checkin_coins.cancel()

    async def place_order(self, payload):
        try:
            # Formatting payload
            del payload['shipping_orders'][0]['logistics']
            del payload['payment_channel_info']
            payload['shipping_orders'][0]['buyer_remark'] = ""
            payload['shoporders'][0]['buyer_remark'] = ""
            payload['shoporders'][0]['ext_ad_info_mappings'] = []
            payload['__raw'] = {}
            payload['_cft'] = [
                    56939
                ]
            payload['captcha_version'] = 1
            payload['can_checkout'] = True
            payload['device_info'] = {
                "device_sz_fingerprint": FINGERPRINT
            }
            payload['disabled_checkout_info'] = {
                "description": "",
                "auto_popup": False,
                "error_infos": []
            }
            payload['selected_payment_channel_data'] = {
                "version": 2,
                "option_info": "",
                "channel_id": 2002700,
                "channel_item_option_info": {
                    "option_info": "30"
                },
                "additional_info": {
                    "reason": "",
                    "channel_blackbox": "{}"
                },
                "text_info": {}
            }
            if payload["shoporders"][0]["items"][0]["insurances"]:
                payload["shoporders"][0]["items"][0]["insurances"][0]["selected"] = False

            async with self.session.post("https://shopee.com.my/api/v4/checkout/place_order", data = json.dumps(payload)) \
                    as response:
                result = await response.json()

                if 'checkoutid' in result:
                    return True
                else:
                    return False
        except Exception as e:
            traceback.print_exc()

    async def get_checkout_info(self, shop_order_id, shopid):
        payload = {
            "_cft": [
                56939
            ],
            "shoporders": [
                {
                    "shop": {
                        "shopid": shopid
                    },
                    "items": [
                        {
                            "itemid": shop_order_id['itemid'],
                            "modelid": shop_order_id['modelid'],
                            "quantity": shop_order_id['quantity'],
                            "add_on_deal_id": shop_order_id['add_on_deal_id'],
                            "is_add_on_sub_item": shop_order_id['is_add_on_sub_item'],
                            "item_group_id": shop_order_id['item_group_id'],
                            "insurances": []
                        }
                    ]
                }
            ],
            "selected_payment_channel_data": {},
            "promotion_data": {
                "use_coins": False,
                "free_shipping_voucher_info": {
                    "free_shipping_voucher_id": 0,
                    "disabled_reason": "",
                    "description": ""
                },
                "platform_vouchers": [],
                "shop_vouchers": [],
                "check_shop_voucher_entrances": True,
                "auto_apply_shop_voucher": False
            },
            "device_info": {
                "device_id": "",
                "device_fingerprint": "",
                "tongdun_blackbox": "",
                "buyer_payment_info": {}
            },
            "tax_info": {
                "tax_id": ""
            }
        }
        async with self.session.post('https://shopee.com.my/api/v4/checkout/get', data = json.dumps(payload)) \
                as response:
            print("Getting checkout info...")
            result = await response.json()
        return await self.place_order(result)

    async def start_checkout(self, shop_order_id, shopid):
        payload = {
            "selected_shop_order_ids": [
                {
                    "shopid": shopid,
                    "item_briefs": [
                        {
                            "itemid": shop_order_id['itemid'],
                            "modelid": shop_order_id['modelid'],
                            "item_group_id": shop_order_id['item_group_id'],
                            "applied_promotion_id": shop_order_id['applied_promotion_id'],
                            "offerid": shop_order_id['offerid'],
                            "price": shop_order_id['origin_cart_item_price'],
                            "quantity": shop_order_id['quantity'],
                            "is_add_on_sub_item": shop_order_id['is_add_on_sub_item'],
                            "add_on_deal_id": shop_order_id['add_on_deal_id'],
                            "status": shop_order_id["status"],
                            "cart_item_change_time": shop_order_id['cart_item_change_time'],
                            "membership_offer_id": shop_order_id['membership_offer_id']
                        }
                    ],
                    "shop_vouchers": []
                }
            ],
            "platform_vouchers": [],
            "free_shipping_voucher_info": None,
            "use_coins": False,
            "sz_device_fingerprint":  FINGERPRINT,
            "support_problematic_groups": True,
            "version": 3
        }
        async with self.session.post('https://shopee.com.my/api/v4/cart/checkout', data = json.dumps(payload)) \
                as response:
            result = await response.json()
            if not result['data']:
                return
        print("Starting checkout...")
        return await self.get_checkout_info(shop_order_id, shopid)

    async def get_cart_info(self):
        payload = {
            "pre_selected_item_list": [],
            "updated_time_filter": {
                "start_time": 0
            },
            "version": 3
        }
        async with self.session.post('https://shopee.com.my/api/v4/cart/get', data = json.dumps(payload)) as response:
            result = await response.json()
            if result['error_message'] != "success":
                return
            print("Checking out " + result['data']['shop_orders'][0]['items'][0]['name'] + "...")
        return await self.start_checkout(result['data']['shop_orders'][0]['items'][0],
                                  result['data']['shop_orders'][0]['shop']['shopid'])

    @app_commands.command(name = "checkout")
    async def add_to_cart(self, interaction: discord.Interaction, link: str, params: Optional[str] = None):
        regex = re.compile(r'-i.\d{9}.(.*?)\?sp')
        itemid = regex.search(link).group(1)
        shopid = await self.get_shopid(link)
        modelid, imageid, name = await self.get_modelid(itemid, params, shopid)

        payload = {
            "quantity": 1,
            "checkout": True,
            "update_checkout_only": False,
            "donot_add_quantity": False,
            "source": "{\"refer_urls\":[]}",
            "add_on_deal_id": None,
            "client_source": 1,
            "shopid": shopid,
            "itemid": itemid,
            "modelid": modelid
        }

        async with self.session.get('https://shopee.com.my/api/v4/cart/add_to_cart ', data = json.dumps(payload)) \
                as response:
            result = await response.json()

            if result['error_msg'] == "":
                checkout_result = self.get_cart_info()
                if checkout_result:
                    embed = discord.Embed(
                        title = "Checkout Successful!",
                        color = discord.Color.green()
                    )
                    embed.set_image(url = f'https://cf.shopee.com.my/file/{imageid}')
                    embed.add_field(
                        name = "Item Name",
                        value = name,
                        inline = False
                    )
                    if params:
                        embed.add_field(
                            name = "Model",
                            value = params,
                            inline = False
                        )
                    interaction.response.send_message(embed = embed)
                else:
                    embed = discord.Embed(
                        title = "Checkout Failed!",
                        color = discord.Color.red()
                    )
                    embed.set_image(url = f'https://cf.shopee.com.my/file/{imageid}')
                    embed.add_field(
                        name = "Item Name",
                        value = name,
                        inline = False
                    )
                    if params:
                        embed.add_field(
                            name = "Model",
                            value = params,
                            inline = False
                        )
                    interaction.response.send_message(embed = embed)
            else:
                interaction.response.send_message("Failed to add item to cart")

    async def get_modelid(self, itemid, params, shopid):
        async with self.session.get(f'https://shopee.com.my/api/v4/item/get?itemid={itemid}&shopid={shopid}]') \
                as response:

            result = await response.json()

            if params:
                for model in result['data']['models']:
                    if model['name'] == params:
                        modelid = model['modelid']
            else:
                modelid = result['data']['models'][0]['modelid']

            imageid = result["data"]["images"][0]
            name = result["data"]["name"]
        return modelid, imageid, name

    async def get_shopid(self, link):
        async with self.session.get(link) as response:
            result = await response.text()
            regex = re.compile(r'shopid":(.*?),"username"')
            shopid = regex.search(result).group(1)

        return shopid

    @app_commands.command(name = "total")
    async def total_purchase(self, interaction: discord.Interaction):
        counter, total_price = 0, 0
        while True:
            url = f"https://shopee.com.my/api/v4/order/get_all_order_and_checkout_list?limit=5&offset={counter}"
            async with self.session.get(url) as response:
                result = await response.json()
            try:
                for order in result['data']['order_data']['details_list']:
                    if order['status']['status_label']['text'] == "label_order_cancelled":
                        continue
                    total_price += order['info_card']['final_total']
            except (KeyError):
                break
            counter += 5

        await interaction.response.send_message(f"Total Amount Spent: RM {total_price / 100000}")

    @app_commands.command(name = "check")
    async def check_task(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Task is running: {self.checkin_coins.is_running()}")

    @tasks.loop(hours = 24)
    async def checkin_coins(self):
        channel = self.bot.get_channel(1003274236590297148)
        payload = {}

        async with self.session.post("https://shopee.com.my/mkt/coins/api/v2/checkin_new", json = payload) as response:
            result = await response.json()

        if result['msg'] == "success" and result['data']['increase_coins'] > 0:
            await channel.send(f"Got {result['data']['increase_coins']} coins")
        else:
            await channel.send(result)

    @app_commands.command(name = "start")
    async def start_task(self, interaction):
        self.checkin_coins.start()

        await interaction.response.send_message("Task started")


async def setup(bot: ShopeeBot):
    await bot.add_cog(Shopee(bot))
