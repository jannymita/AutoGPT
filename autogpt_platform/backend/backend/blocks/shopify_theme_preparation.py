import os
import shutil
from datetime import datetime
import zipfile
import boto3
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
        theme_id: str = SchemaField(
            description="The ID of the theme to user selected",
        )
        theme_params: str = SchemaField(
            description="The parameters of the theme",
        )
        theme_params_extra: dict[str, str] = SchemaField(
            description="Extra parameters of the theme",
            default={},
        )

    class Output(BlockSchema):
        shop_name: str = SchemaField(description="The shop name on Shopify")
        theme_id: str = SchemaField(description="The ID of the theme to user selected")
        theme_zip_url: str = SchemaField(description="The public url of a zip file containing the theme")

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
                {"theme_params": "\{\}"},
                {"theme_params_extra": {}},
            ],
            test_output=[
                ("shop_name", "3tn-demo"),
                ("theme_zip_url", "https://3tn-autogpt.s3.ap-southeast-1.amazonaws.com/shopify/theme/20250123/ks-bootshop-master.zip"),
            ],
        )

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
      url = self.process_and_upload(input_data.shop_name, input_data.theme_id, input_data.theme_params, input_data.theme_params_extra)
      yield "shop_name", input_data.shop_name
      yield "theme_id", input_data.theme_id
      yield "theme_zip_url", url

    def process_and_upload(self, shopname: str, theme_id: str, theme_params_text: str, theme_params_extra: dict[str, str]):
      # Define constants
      bucket_name = "3tn-autogpt"
      s3_region = "ap-southeast-1"
      s3_folder = "shopify/theme"

      temp_dir = "/var/tmp/templates"
      # Ensure temporary directory exists
      if not os.path.exists(temp_dir):
          os.makedirs(temp_dir)

      theme_template_dir = f"/app/autogpt_platform/backend/backend/templates/{theme_id}"

      # Create a timestamp for uniqueness
      timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
      zip_filename = f"{theme_id}-{shopname}-{timestamp}.zip"  # Corrected zip filename without path
      zip_file_path = os.path.join(temp_dir, zip_filename)  # Full path for zipping
      theme_dir = os.path.join(temp_dir, f"{theme_id}_{timestamp}")

      # Backup the folder before making changes
      if os.path.exists(theme_template_dir):
          try:
              shutil.copytree(theme_template_dir, theme_dir)
          except Exception as e:
              raise Exception(f"Unable to process the selected theme {theme_id}: {e}")
      else:
          raise FileNotFoundError(f"The theme {theme_id} does not exist")
      
      theme_params = json.loads(theme_params_text)
      for filename, kv in theme_params.items():
          file_path = os.path.join(theme_dir, filename)
          with open(file_path, "r+") as file:
              file_content = file.read()
              for key, value in kv.items():
                  file_content = file_content.replace(key, value)
              for key, value in theme_params_extra.items():
                  file_content = file_content.replace("{{" + key + "}}", value)
              file.seek(0)
              file.write(file_content)
              file.truncate()
          
      # Step 3: Zip the modified repository
      try:
          with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
              for root, _, files in os.walk(theme_dir):
                  for file in files:
                      file_path = os.path.join(root, file)
                      arcname = os.path.relpath(file_path, start=theme_dir)
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
          shutil.rmtree(theme_dir)  # Remove the backup directory
          print(f"Deleted local zip file and backup directory")
      except Exception as e:
          raise Exception(f"Failed during cleanup: {e}")

      # Step 6: Return the S3 URL
      s3_url = f"https://{bucket_name}.s3.{s3_region}.amazonaws.com/{s3_key}"
      return s3_url
     