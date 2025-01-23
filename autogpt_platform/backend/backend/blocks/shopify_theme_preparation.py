import os
import shutil
from datetime import datetime
import zipfile
import boto3
import subprocess
import json

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class ShopifyThemePreparationBlock(Block):
    block_id: str = "70692a84-8716-4bd3-8e33-488e7f60a6b2"

    class Input(BlockSchema):
        shop_name: str = SchemaField(
            description="The name of Shopify shop and subdomain",
        )
        admin_api_key: str = SchemaField(description="Shopify app API key for Admin API")
        theme_template_index_json: str = SchemaField(
            description="The theme template index json",
        )

    class Output(BlockSchema):
        shop_name: str = SchemaField(description="The shop name on Shopify")
        theme_zip_url: str = SchemaField(description="The public url of a zip file containing the theme")
        collections: dict = SchemaField(
          description="The collections to create",
        )


    def __init__(self):
        super().__init__(
            id=ShopifyThemePreparationBlock.block_id,
            description="This block prepare a theme for a Shopify store.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ShopifyThemePreparationBlock.Input,
            output_schema=ShopifyThemePreparationBlock.Output,
            test_input=[
                {"shop_name": "3tn-demo"},
                {"admin_api_key": "*********************************************"},
                {"theme_template_index_json": "\{\}"},
            ],
            test_output=[
                ("shop_name", "3tn-demo"),
                ("theme_zip_url", "https://3tn-autogpt.s3.ap-southeast-1.amazonaws.com/shopify/theme/20250123/ks-bootshop-master.zip"),
                ("collections", {"collection_kRQqkR": {"type": "collection", "settings": {"collection": "sale", "title": ""}}})
            ],
        )

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
      url = self.process_and_upload(input_data.theme_template_index_json)
      collections = self.get_collections(input_data.theme_template_index_json)
      yield "shop_name", input_data.shop_name
      yield "theme_zip_url", url
      yield "collections", collections
    
    def process_and_upload(self,config_json: str):
        # Define constants
        repo_url = "https://github.com/kondasoft/ks-bootshop.git"
        bucket_name = "3tn-autogpt"
        s3_region = "ap-southeast-1"
        s3_folder = "shopify/theme"

        # Create a timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        zip_filename = f"ks-bootshop-{timestamp}.zip"
        repo_dir = "ks-bootshop"

        # Step 1: Clone the repository
        try:
          if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)  # Clean up any existing directory
          subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to clone repository: {e}")

        # Step 2: Replace data in templates/index.json
        template_path = os.path.join(repo_dir, "templates", "index.json")
        if os.path.exists(template_path):
          with open(template_path, "w") as file:
            file.write(config_json)
        else:
          raise FileNotFoundError(f"Template file not found at {template_path}")

        # Step 3: Zip the modified repository
        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
          for root, _, files in os.walk(repo_dir):
            for file in files:
              file_path = os.path.join(root, file)
              arcname = os.path.relpath(file_path, start=repo_dir)
              zipf.write(file_path, arcname)

        # Step 4: Upload to S3
        s3 = boto3.client("s3", region_name=s3_region)
        s3_key = f"{s3_folder}/{datetime.now().strftime('%Y%m%d')}/{zip_filename}"

        try:
          s3.upload_file(zip_filename, bucket_name, s3_key)
        except Exception as e:
          raise Exception(f"Failed to upload to S3: {e}")

        # Step 5: Delete the local zip file
        os.remove(zip_filename)
        shutil.rmtree(repo_dir)  # Clean up the cloned repository

        # Step 6: Return the S3 URL
        s3_url = f"https://{bucket_name}.s3.{s3_region}.amazonaws.com/{s3_key}"
        return s3_url
    
    @staticmethod
    def get_collections(data) -> dict:
      try:
        parsed_data = json.loads(data)  # Parse the JSON string into a dictionary
      except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data: {e}")
      collections_section = parsed_data.get("sections", {}).get("featured_collections_n3Br7m", {})
      blocks = collections_section.get("blocks", {})
      
      return blocks
