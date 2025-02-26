import requests
from datetime import datetime
import shopify
import json
from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class ShopifyUploadImageBlock(Block):
    class Input(BlockSchema):
        shop_name: str = SchemaField(
            description="The Shopify store name",
        )
        admin_api_key: str = SchemaField(
            description="The API key of the Shopify store",
        )
        image_url: str = SchemaField(
            description="The URL of the image to upload",
        )

    class Output(BlockSchema):
        image_name: str = SchemaField(
            description="The name of the uploaded image",
        )
        image_id: str = SchemaField(
            description="The id of the uploaded image",
        )

    def __init__(self):
        super().__init__(
            id="a3c8fbc9-d7e8-432b-a4a1-fb4db9f8b1a1",
            description="This block uploads an image to a Shopify store.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ShopifyUploadImageBlock.Input,
            output_schema=ShopifyUploadImageBlock.Output,
            test_input={
                "shop_name": "shop-1.myshopify.com",
                "admin_api_key": "your-admin-api-key",
                "image_url": "https://example.com/image.jpg"
            },
            test_output={
                "image_name": "image.jpg",
                "image_id": ""
            }
        )

    def upload_image(self, shop_name: str, admin_api_key: str, image_url: str) -> dict:
        if not all([shop_name, admin_api_key, image_url]):
            raise ValueError("Missing one or more required inputs: shop_name, admin_api_key, or image_url")

        url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/graphql.json"
        query = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files {
              alt
              id
              createdAt
              fileStatus
              preview {
                image {
                  url
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "files": [
                {
                    "alt": "out-0.webp",
                    "contentType": "IMAGE",
                    "originalSource": image_url
                }
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": admin_api_key
        }

        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("errors") or data["data"]["fileCreate"]["userErrors"]:
                raise Exception("Error uploading image: " + str(data))
            file_data = data["data"]["fileCreate"]["files"][0]
            return {
                "image_name": file_data["alt"],
                "image_id": file_data["id"]
            }
        else:
            raise Exception(f"Failed to upload image: {response.text}")
    
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            shop_name = input_data.shop_name
            admin_api_key = input_data.admin_api_key
            image_url = input_data.image_url

            result = self.upload_image(shop_name, admin_api_key, image_url)

            yield "image_name", result["image_name"]
            yield "image_id", result["image_id"]
        except Exception as e:
            yield "error", f"An error occurred: {e}"

class ShopifyThemeInstallBlock(Block):
    api_version = "2025-01"
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
        theme_name: str = SchemaField(
            description="The name of the installed Shopify theme",
            default=None
        )

    class Output(BlockSchema):
        shop_name: str = SchemaField(
            description="The name of the Shopify store",
        )
        theme_id: str = SchemaField(
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
    def install_theme(theme_link: str, shop_name: str, theme_name: str) -> dict:
        """Install a theme using the Shopify GraphQL API."""

        # GraphQL mutation to install the theme
        query = """
            mutation themeCreate($source: URL!, $name: String!) {
                themeCreate(source: $source, name: $name) {
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
            "source": theme_link,
            "name": theme_name if theme_name else shop_name
        }

        try:
            # Execute the GraphQL mutation
            response = shopify.GraphQL().execute(query, params)

            # Parse the response as JSON (if necessary)
            if isinstance(response, str):
                response = json.loads(response)  # Ensure the response is parsed into a dictionary

            # Check for errors in the response
            if 'data' in response and 'themeCreate' in response['data']:
                theme_data = response['data']['themeCreate']['theme']
                if theme_data:
                    return {
                        "shop_name": shop_name,
                        "theme_id": theme_data.get("id"),
                    }
                else:
                    # Handle user errors if any
                    errors = response['data']['themeCreate']['userErrors']
                    raise Exception(f"Error installing theme: {errors}")
            else:
                raise Exception("Failed to install theme: Unknown error")
        except json.JSONDecodeError:
            raise Exception("Error: Response is not valid JSON")
        except Exception as e:
            raise Exception(f"Error occurred while installing theme: {str(e)}")         
    
    
    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            # Ensure that the input_data contains the required fields
            theme_link = input_data.theme_link
            shop_name = input_data.shop_name
            admin_api_key = input_data.admin_api_key
            theme_name = input_data.theme_name if input_data.theme_name else shop_name

            # Set up the Shopify session
            shop_url = f"https://{shop_name}.myshopify.com"
            session = shopify.Session(shop_url, self.api_version, admin_api_key)
            shopify.ShopifyResource.activate_session(session)

            # Call the install_theme method with the extracted input data
            result = self.install_theme(theme_link, shop_name, theme_name)

            yield "shop_name", result["shop_name"]
            yield "theme_id", result["theme_id"]
            yield "theme_name", theme_name
        except Exception as e:
            yield "error", f"An error occurred: {e}"
        finally:
            # Clear the session after use
            shopify.ShopifyResource.clear_session()
            
