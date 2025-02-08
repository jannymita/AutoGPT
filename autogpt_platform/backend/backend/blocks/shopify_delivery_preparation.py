from typing import Any
import json
import shopify
from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class ShopifyDeliveryPreparationBlock(Block):
    api_version: str = "2025-01"

    class Input(BlockSchema):
        shop_name: str = SchemaField(
            description="The name of Shopify shop and subdomain",
        )
        admin_api_key: str = SchemaField(description="The API key of the Shopify store")

    class Output(BlockSchema):
        markets: list[Any] = SchemaField(description="A list markets of a Shopify store")
        error: str = SchemaField(description="Error message if the API call failed.")

    def __init__(self):
        super().__init__(
            id="a42432a2-2c57-4685-b823-ffc57d7a9f8b",
            description="This block prepare Shopify delivery settings.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ShopifyDeliveryPreparationBlock.Input,
            output_schema=ShopifyDeliveryPreparationBlock.Output,
            test_input={
                "shop_name": "your-shop-name.myshopify.com",
                "admin_api_key": "your-admin-api-key",
            },
            test_output={
                "markets": [
                    {
                        "id": "gid://shopify/Market/90370343225",
                        "handle": "international",
                        "name": "International",
                        "enabled": True
                    }
                ]
            },
        )
        
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        """Run the block with the provided input data."""
        try:
            shop_url = f"https://{input_data.shop_name}.myshopify.com"
            session = shopify.Session(
                shop_url, 
                self.api_version,
                input_data.admin_api_key
            )
            shopify.ShopifyResource.activate_session(session)
            
            # Validate the input data
            markets = self.get_markets()

            for i, market in enumerate(markets):
                if not market["enabled"]:
                    markets[i] = self.enable_markets(market)
            yield "markets", markets

        except ValueError as ve:
            # Handle validation errors
            yield "error", f"Validation error: {ve}"

        except Exception as e:
            # Handle unexpected errors
            yield "error", f"An unexpected error occurred: {e}"
        finally:
            shopify.ShopifyResource.clear_session()

    def get_markets(self) -> list[Any]:
        query = "query AllMarkets {  markets(first: 100) {    nodes {      id      handle      name      enabled    }  }}"
        params = {}
        response = shopify.GraphQL().execute(query, params)

        raw = json.loads(response)
        data = raw["data"]

        nodes = data.get("markets", {}).get("nodes", [])
        if not nodes:
            raise ValueError("No markets found")

        return nodes

    def enable_markets(self, market: Any) -> Any:
        query = "mutation marketUpdate($id: ID!, $input: MarketUpdateInput!) {  marketUpdate(id: $id, input: $input) {    market {     id      handle      name      enabled    }    userErrors {      field      message    }  }}"
        params = {
            "id": market["id"],
            "input": { 
                "enabled": True
            }
        }
        response = shopify.GraphQL().execute(query, params)

        raw = json.loads(response)
        data = raw["data"]

        if data.get("marketUpdate", {}).get("userErrors", None):
            raise ValueError("Failed to enable market", data["marketUpdate"]["userErrors"].get("message"))
        
        return data.get("marketUpdate", {}).get("market", {})
