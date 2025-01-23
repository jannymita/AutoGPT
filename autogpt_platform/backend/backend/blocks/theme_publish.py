from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField
import requests
import json
import time

class ThemePublishBlock(Block):
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
    
    @staticmethod
    def publish_theme(theme_id, shop_name, admin_api_key):
        url_publish = f"https://{shop_name}.myshopify.com/admin/api/2025-01/themes/{theme_id}.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": admin_api_key,
        }

        try:
            payload = {"theme": {"role": "main"}}
            response_publish = requests.put(url_publish, json=payload, headers=headers)
            response_publish.raise_for_status()

            # Return the success response
            return {"theme_id": theme_id}

        except requests.exceptions.RequestException as req_err:
            raise Exception(f"Request error occurred: {req_err}")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")

    @staticmethod
    def wait_for_theme_installation(theme_id, shop_name, admin_api_key, timeout=300, interval=10):
        """
        Wait for the theme installation to complete.

        :param theme_id: ID of the theme to check.
        :param shop_name: Shopify store name.
        :param admin_api_key: Admin API key for authentication.
        :param timeout: Maximum time to wait for installation (in seconds).
        :param interval: Time interval between checks (in seconds).
        :return: None
        :raises Exception: If installation doesn't complete within the timeout.
        """
        url_themes = f"https://{shop_name}.myshopify.com/admin/api/2025-01/themes.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": admin_api_key,
        }

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(url_themes, headers=headers)
                response.raise_for_status()
                themes = response.json().get("themes", [])

                # Check the status of the specified theme
                theme = next((t for t in themes if t["id"] == int(theme_id)), None)
                if not theme:
                    raise Exception(f"Theme with ID {theme_id} not found.")
                if not theme["processing"]:
                    print("Theme installation completed.")
                    return  # Installation is complete

                print("Theme installation still in progress. Waiting...")
                time.sleep(interval)  # Wait before the next check
            except requests.exceptions.RequestException as req_err:
                raise Exception(f"Request error occurred: {req_err}")

        raise Exception("Theme installation did not complete within the timeout period.") 
        
            
    
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            # Ensure that the input_data contains the required fields
            theme_id = input_data.theme_id
            shop_name = input_data.shop_name
            admin_api_key = input_data.admin_api_key

            print(f"Publishing theme with ID: {theme_id} for shop: {shop_name}")
            self.wait_for_theme_installation(theme_id, shop_name, admin_api_key)

            # Call the install_theme method with the extracted input data
            self.publish_theme(theme_id, shop_name, admin_api_key)

            yield "theme_id", theme_id,
            yield "shop_link", f"https://{shop_name}.myshopify.com"
        except Exception as e:
            yield "error", f"An error occurred: {e}"
