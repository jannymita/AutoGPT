import os
import shutil
from datetime import datetime
import zipfile
import boto3
import subprocess
import json
import stat

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
      url = self.process_and_upload(input_data.theme_template_index_json,input_data.shop_name)
      collections = self.get_collections(input_data.theme_template_index_json)
      yield "shop_name", input_data.shop_name
      yield "theme_zip_url", url
      yield "collections", collections

    def process_and_upload(self, config_json: str, shopname: str):
      # Define constants
      repo_url = "https://github.com/kondasoft/ks-bootshop.git"
      bucket_name = "3tn-autogpt"
      s3_region = "ap-southeast-1"
      s3_folder = "shopify/theme"

      # Create a timestamp for uniqueness
      timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
      temp_dir = "/var/tmp/templates"
      zip_filename = f"ks-bootshop-{shopname}-{timestamp}.zip"  # Corrected zip filename without path
      zip_file_path = os.path.join(temp_dir, zip_filename)  # Full path for zipping
      backup_dir = os.path.join(temp_dir, f"ks-bootshop_backup_{timestamp}")

      repo_dir = "/app/autogpt_platform/backend/backend/blocks/ks-bootshop"
      
      # Ensure temporary directory exists
      if not os.path.exists(temp_dir):
          os.makedirs(temp_dir)

      # Backup the folder before making changes
      if os.path.exists(repo_dir):
          try:
              shutil.copytree(repo_dir, backup_dir)
              print(f"Backup created at: {backup_dir}")
          except Exception as e:
              raise Exception(f"Failed to create backup: {e}")
      else:
          raise FileNotFoundError(f"Repository directory not found: {repo_dir}")

      # Step 2: Replace data in templates/index.json
      template_path = os.path.join(backup_dir, "templates", "index.json")
      if os.path.exists(template_path):
          with open(template_path, "w") as file:
              file.write(config_json)
          print(f"Updated JSON file at: {template_path}")
      else:
          raise FileNotFoundError(f"Template file not found at {template_path}")

      # Step 3: Zip the modified repository
      try:
          with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
              for root, _, files in os.walk(backup_dir):
                  for file in files:
                      file_path = os.path.join(root, file)
                      arcname = os.path.relpath(file_path, start=backup_dir)
                      zipf.write(file_path, arcname)
          print(f"Zipped folder to {zip_file_path}")
      except Exception as e:
          raise Exception(f"Failed to zip repository: {e}")

      # Step 4: Upload the ZIP file to S3
      s3 = boto3.client("s3", region_name=s3_region)
      s3_key = f"{s3_folder}/{datetime.now().strftime('%Y%m%d')}/{zip_filename}"  # Use only the filename, not the full path

      try:
          s3.upload_file(zip_file_path, bucket_name, s3_key)
          print(f"Uploaded to S3: {s3_key}")
      except Exception as e:
          raise Exception(f"Failed to upload to S3: {e}")

      # Step 5: Clean up local files and folders
      try:
          os.remove(zip_file_path)  # Remove the zip file
          shutil.rmtree(backup_dir)  # Remove the backup directory
          print(f"Deleted local zip file and backup directory")
      except Exception as e:
          raise Exception(f"Failed during cleanup: {e}")

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
