import requests
from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class ShopifyThemeInstallBlock(Block):
    class Input(BlockSchema):
        theme_link: str = SchemaField(
            description="The link to the Shopify theme to install",
        )
        shop_name: str = SchemaField(
            description="The Shopify store name",
        )
        admin_api_key: str = SchemaField(
            description="The API key of the Shopify store",
        )

    class Output(BlockSchema):
        shop_name: str = SchemaField(
            description="The name of the Shopify store",
        )
        theme_id: int = SchemaField(
            description="The ID of the installed Shopify theme",
        )
        theme_name: str = SchemaField(
            description="The name of the installed Shopify theme",
        )

    def __init__(self):
        super().__init__(
            id="d7cbcb27-c27a-4cba-bc6d-c5bac9b89f31",
            description="This block installs a Shopify theme.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ShopifyThemeInstallBlock.Input,
            output_schema=ShopifyThemeInstallBlock.Output,
            test_input={
                "theme_link": "https://example.com/path-to-theme.zip",
                "shop_name": "shop-1.myshopify.com",
                "admin_api_key": "your-admin-api-key"
            },
            test_output={
                "shop_name": "shop-1.myshopify.com",
                "theme_id": 123456789,
                "theme_name": "New Theme"
            }
        )

    def install_theme(self, theme_link: str, shop_name: str, admin_api_key: str) -> dict:
        if not all([theme_link, shop_name, admin_api_key]):
            raise ValueError("Missing one or more required inputs: theme_link, shop_name, or admin_api_key")

        url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/themes.json"
        payload = {
            "theme": {
                "name": "New Theme",
                "src": theme_link,
                "role": "unpublished"
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": admin_api_key
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            theme_data = response.json().get("theme", {})
            return {
                "shop_name": shop_name,
                "theme_id": theme_data.get("id"),
                "theme_name": theme_data.get("name"),
            }
        else:
            raise Exception(f"Failed to install theme: {response.text}")
    
    
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            # Ensure that the input_data contains the required fields
            theme_link = input_data.theme_link
            shop_name = input_data.shop_name
            admin_api_key = input_data.admin_api_key

            # Call the install_theme method with the extracted input data
            result = self.install_theme(theme_link, shop_name, admin_api_key)

            yield "shop_name", result["shop_name"]
            yield "theme_id", result["theme_id"]
            yield "theme_name", result["theme_name"]
        except Exception as e:
            yield "error", f"An error occurred: {e}"
