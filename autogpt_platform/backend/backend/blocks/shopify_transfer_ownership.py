import os
import requests
import base64
import time
from backend.data import redis

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField


class ShopifyTransferOwnershipBlock(Block):
    block_id: str = "add1e817-4118-4fab-98cb-32f31597ff34"

    class Input(BlockSchema):
        shop_name: str = SchemaField(
            description="The name of Shopify shop and subdomain",
        )
        wait_for_complete_seconds: int = SchemaField(
            description="The number of seconds to wait for the invite to complete",
            default=5,
        )
        email: str = SchemaField(
            description="The staff email you want to invite",
        )
        first_name: str = SchemaField(
            description="The staff first name",
        )
        last_name: str = SchemaField(
            description="The staff last name",
        )

    class Output(BlockSchema):
        shop_name: str = SchemaField(description="The shop that we want to transfer ownership")
        user_id: str = SchemaField(description="The user id of new owner")

    def __init__(self):
        oauth_url = os.getenv("SHOPIFY_INTEGRATION_OAUTH_URL")
        if not oauth_url:
            raise EnvironmentError("Environment variable 'SHOPIFY_INTEGRATION_OAUTH_URL' is not set.")
        self.oauth_url = oauth_url
        self.redis = redis.get_redis()

        super().__init__(
            id=ShopifyTransferOwnershipBlock.block_id,
            description="This block transfers ownership of a Shopify store ot new owner.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ShopifyTransferOwnershipBlock.Input,
            output_schema=ShopifyTransferOwnershipBlock.Output,
            test_input=[
                {"shop_name": "3tn-demo", "email": "tuan.nguyen930708+1@gmail.com", "first_name": "Tuan", "last_name": "Nguyen"},
            ],
            test_output=[
                ("shop_name", "3tn-demo"),
                ("user_id", "gid://shopify/StaffMember/116287635752"),
            ],
        )


    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        if os.getenv("DEBUG", "false").lower() == "true":
            yield "shop_name", input_data.shop_name
            yield "user_id", "gid://shopify/StaffMember/116287635752"
            return
        
        user_id = self.transfer(input_data.shop_name, input_data.email, input_data.first_name, input_data.last_name)

        # Delay for the specified amount of time
        time.sleep(input_data.wait_for_complete_seconds)
        yield "shop_name", input_data.shop_name
        yield "user_id", user_id
    

    def transfer(self, shop_name: str, email: str, first_name: str, last_name: str):
        partner_password = os.getenv("SHOPIFY_INTEGRATION_PARTNER_PASSWORD")
        if not partner_password:
            raise EnvironmentError("Partner credentials is not set | Code: 001")

        encoded_cookie = self.redis.get("SHOPIFY_INTEGRATION_STORE_COOKIE")
        if not encoded_cookie:
            raise EnvironmentError("Environment variable SHOPIFY_INTEGRATION_STORE_COOKIE is missing.")
        
        cookie = base64.b64decode(encoded_cookie).decode("utf-8")

        csrf_token = self.redis.get("SHOPIFY_INTEGRATION_STORE_CSRF_TOKEN")
        if not csrf_token:
            raise EnvironmentError("Partner credentials is not set | Code: 002")
        
        # API endpoint
        url = f"https://admin.shopify.com/api/shopify/{shop_name}?operation=StaffMemberOwnershipTransfer&type=mutation"
        
        # Headers
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "caller-pathname": "/store/{shop_name}/settings/account",
            "content-type": "application/json",
            "cookie": cookie,
            "origin": "https://admin.shopify.com",
            "priority": "u=1, i",
            "referer": "https://admin.shopify.com/store/{shop_name}/settings/account",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "target-manifest-route-id": "settings-account:index",
            "target-pathname": "/store/:storeHandle/settings/account",
            "target-slice": "account-section",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "x-csrf-token": csrf_token,
            "x-shopify-web-force-proxy": "1",
        }

        # Body
        payload = {
            "operationName": "StaffMemberOwnershipTransfer",
            "variables": {
                "input": {
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "password": partner_password
                }
            },
            "query": (
                "mutation StaffMemberOwnershipTransfer($input: StaffMemberOwnershipTransferInput!) {"
                "  staffMemberOwnershipTransfer(input: $input) {"
                "    userErrors {"
                "      field"
                "      message"
                "      __typename"
                "    }"
                "    staffMember {"
                "      id"
                "      accountType"
                "      name"
                "      __typename"
                "    }"
                "    __typename"
                "  }"
                "}"
            )
        }
        # Send POST request
        response = requests.post(url, headers=headers, json=payload)
        
        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text} | {payload} | {csrf_token}")

        raw = response.json()
        data = raw["data"]
        if data and data["staffMemberOwnershipTransfer"] and data["staffMemberOwnershipTransfer"]["staffMember"] and data["staffMemberOwnershipTransfer"]["staffMember"]["id"]:
            return data["staffMemberOwnershipTransfer"]["staffMember"]["id"]
        else:
            raise Exception(f"Failed to invite staff to store {shop_name}: {raw}")
