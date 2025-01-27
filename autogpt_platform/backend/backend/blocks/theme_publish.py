from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField
import requests
import time
import shopify
import json

class ThemePublishBlock(Block):
    api_version = "2025-01"
    class Input(BlockSchema):
        theme_id: str = SchemaField(
            description="The ID of the theme to publish",
        )
        shop_name: str = SchemaField(
            description="The Shopify store name",
        )
        admin_api_key: str = SchemaField(
            description="The API key of the Shopify store",
        )

    class Output(BlockSchema):
        theme_id: str = SchemaField(
            description="The ID of the published theme",
        )
        shop_link: str = SchemaField(
            description="The link to the Shopify store",
        )

    def __init__(self):
        super().__init__(
            id="007045c5-c900-4a40-b77b-05d18d308d66",
            description="This block publishes a Shopify theme.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ThemePublishBlock.Input,
            output_schema=ThemePublishBlock.Output,
            test_input={
                "theme_id": "3f293986-929d-4422-bd0d-5515a16db2fc",
                "shop_name": "shop-1.myshopify.com",
                "admin_api_key": "your-admin-api-key"
            },
            test_output={
                "theme_id": "3f293986-929d-4422-bd0d-5515a16db2fc",
                "shop_link": "https://shop-1.myshopify.com"
            }
        )
    
    def publish_theme(self, theme_id, shop_name, admin_api_key):
        """Publish a theme as the main theme using the Shopify GraphQL API."""

        query = """
        mutation themePublish($id: ID!) {
                themePublish(id: $id) {
                    theme {
                    id
                    }
                    userErrors {
                    code
                    field
                    message
                    }
                }
            }
        """

        params = {
            "id": theme_id
        }

        try:
            # Execute the GraphQL mutation to publish the theme
            response = shopify.GraphQL().execute(query, params)
            # Parse the response if it is a string
            if isinstance(response, str):
                response = json.loads(response)

            # Check if there are errors in the response
            if 'data' in response and 'themePublish' in response['data']:
                theme = response['data']['themePublish']['theme']
                if theme:
                    print(f"Theme with ID {theme_id} has been set as the main theme.")
                    return {"theme_id": theme_id}
                else:
                    errors = response['data']['themePublish']['userErrors']
                    raise Exception(f"Error publishing theme '{theme_id}': {errors}")
            else:
                raise Exception(f"Unknown error while publishing theme '{theme_id}'")

        except Exception as e:
            raise Exception(f"Error occurred while publishing theme '{theme_id}': {str(e)}")

    def wait_for_theme_installation(self, theme_id):

        timeout=300
        interval=10

        query = """
        query checkThemeInstallation($themeId: ID!) {
            theme(id: $themeId) {
                id
                processing
            }
        }
        """

        params = {
            "themeId": theme_id
        }

        start_time = time.time()

        while time.time() - start_time < float(timeout):
            try:
                # Execute the GraphQL query to check the theme status
                response = shopify.GraphQL().execute(query, params)

                # Parse the response if it is a string
                if isinstance(response, str):
                    response = json.loads(response)

                # Check if theme processing status is available
                if 'data' in response and 'theme' in response['data']:
                    theme = response['data']['theme']
                    if not theme['processing']:
                        print("Theme installation completed.")
                        return  # Installation is complete

                    print("Theme installation still in progress. Waiting...")
                    time.sleep(interval)  # Wait before the next check
                else:
                    raise Exception(f"Error retrieving theme status for theme '{theme_id}'.")

            except Exception as e:
                raise Exception(f"Error occurred while checking theme installation status: {str(e)}")

        raise Exception("Theme installation did not complete within the timeout period.")
        
            
    
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            # Ensure that the input_data contains the required fields
            theme_id = input_data.theme_id
            shop_name = input_data.shop_name
            admin_api_key = input_data.admin_api_key
            # Set up the Shopify session
            shop_url = f"https://{shop_name}.myshopify.com"
            session = shopify.Session(shop_url, self.api_version, admin_api_key)
            shopify.ShopifyResource.activate_session(session)

            print(f"Publishing theme with ID: {theme_id} for shop: {shop_name}")
            self.wait_for_theme_installation(theme_id)

            # Call the publish_theme method with the extracted input data
            self.publish_theme(theme_id, shop_name, admin_api_key)

            yield "theme_id", theme_id,
            yield "shop_link", f"https://{shop_name}.myshopify.com"
        except Exception as e:
            yield "error", f"An error occurred: {e}"
        finally:
            shopify.ShopifyResource.clear_session()
