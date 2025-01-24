import requests
import shopify
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

    @staticmethod
    def install_theme(theme_link: str, shop_name: str, admin_api_key: str) -> dict:
        """Install a theme using the Shopify GraphQL API."""

        # GraphQL mutation to install the theme
        query = """
        mutation installTheme($themeSrc: String!) {
            themeCreate(input: {
                name: "New Theme",
                src: $themeSrc,
                role: UNPUBLISHED
            }) {
                theme {
                    id
                    name
                    role
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        params = {
            "themeSrc": theme_link
        }

        try:
            # Execute the GraphQL mutation
            response = shopify.GraphQL().execute(query, params)

            # Check for errors in the response
            if 'data' in response and 'themeCreate' in response['data']:
                theme_data = response['data']['themeCreate']['theme']
                if theme_data:
                    return {
                        "shop_name": shop_name,
                        "theme_id": theme_data.get("id"),
                        "theme_name": theme_data.get("name"),
                    }
                else:
                    # Handle user errors if any
                    errors = response['data']['themeCreate']['userErrors']
                    raise Exception(f"Error installing theme: {errors}")
            else:
                raise Exception("Failed to install theme: Unknown error")
        except Exception as e:
            raise Exception(f"Error occurred while installing theme: {str(e)}")
    
    
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            # Ensure that the input_data contains the required fields
            theme_link = input_data.theme_link
            shop_name = input_data.shop_name
            admin_api_key = input_data.admin_api_key

            # Set up the Shopify session
            shop_url = f"https://{shop_name}.myshopify.com"
            session = shopify.Session(shop_url, self.api_version, admin_api_key)
            shopify.ShopifyResource.activate_session(session)


            # Call the install_theme method with the extracted input data
            result = self.install_theme(theme_link, shop_name, admin_api_key)

            yield "shop_name", result["shop_name"]
            yield "theme_id", result["theme_id"]
            yield "theme_name", result["theme_name"]
        except Exception as e:
            yield "error", f"An error occurred: {e}"
