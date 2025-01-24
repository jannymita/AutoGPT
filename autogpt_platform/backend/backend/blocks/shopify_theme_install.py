import requests
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
                "image_name": "image.jpg"
            }
        )

    def upload_image(self, shop_name: str, admin_api_key: str, image_url: str) -> dict:
        if not all([shop_name, admin_api_key, image_url]):
            raise ValueError("Missing one or more required inputs: shop_name, admin_api_key, or image_url")

        url = f"https://{shop_name}/admin/api/2025-01/files.json"
        payload = {
            "file": {
                "alt": "Uploaded Image",
                "contentType": "IMAGE",
                "originalSource": image_url
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": admin_api_key
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            file_data = response.json().get("file", {})
            return {
                "image_name": file_data.get("filename", "unknown.jpg")
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
        except Exception as e:
            yield "error", f"An error occurred: {e}"

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
