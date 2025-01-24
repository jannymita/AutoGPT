import os
import re
import base64
import json
from typing import Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from backend.util.google import search_image_urls

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import BlockSecret, SchemaField, SecretField

class ShopifyProductsNormalizationBlock(Block):
    block_id: str = "b8ef4073-0936-49c1-9fcd-3b8a5a12787d"
    scopes: list[str] = ["https://www.googleapis.com/auth/spreadsheets"]

    class Input(BlockSchema):
        spreadsheet_id: str = SchemaField(
            description="The ID of the spreadsheet that contains products",
        )
        range: str = SchemaField(
            description="The A1 notation of the range to write",
            default="sheet1!A1:Z100"
        )

    class Output(BlockSchema):
        spreadsheet_id: str = SchemaField(
            description="The ID of the spreadsheet that contains products",
        )
        image_urls: list[str] = SchemaField(
            description="The list of image url we added",
        )

    def __init__(self):
        super().__init__(
            id=ShopifyProductsNormalizationBlock.block_id,
            description="This block create normalized products in a products import template on Spreadsheet.",
            categories={BlockCategory.SHOPIFY},
            input_schema=ShopifyProductsNormalizationBlock.Input,
            output_schema=ShopifyProductsNormalizationBlock.Output,
            test_input=[
                {"spreadsheet_id": "95d29dd9-cb29-42fa-8632-058270978e21"},
            ],
            test_output=[
                {"spreadsheet_id": "95d29dd9-cb29-42fa-8632-058270978e21", "image_urls": []},
            ],
        )

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        sheet = self.connect()
        image_urls = self.normalize_products(sheet, self.extract_spreadsheet_id(input_data.spreadsheet_id), input_data.range)
        yield "spreadsheet_id", input_data.spreadsheet_id
        yield "image_urls", image_urls
        
    @staticmethod
    def extract_spreadsheet_id(spreadsheet_source: str) -> str:
        pattern = r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)/"
        match = re.search(pattern, spreadsheet_source)
        if match:
            return match.group(1)
        return spreadsheet_source
    
    @staticmethod
    def connect() -> Any:
        sa_base64 = os.getenv("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT")
        if not sa_base64:
            raise Exception("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT is not set")

        # Decode the base64 service account key
        sa_json = base64.b64decode(sa_base64).decode('utf-8')
        service_account_info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, 
            scopes=ShopifyProductsNormalizationBlock.scopes
        )

        service = build("sheets", "v4", credentials=credentials)
        return service.spreadsheets()
    
    def normalize_products(self, sheet: Any, spreadsheet_id: str, range: str) -> list[str]:
        image_urls = []

        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range).execute()
        values = result.get('values', [])

        if not values:
            print("No data found in the spreadsheet.")
            return image_urls

         # Extract headers and data
        headers = values[0]
        data = values[1:]

        # Check if 'Image Url' column exists
        if 'Image Url' not in headers:
            print("The 'Image Url' column is missing from the spreadsheet.")
            return

        # Find the index of the 'Image Url' and 'id' columns
        image_url_index = headers.index('Image Url')

        # Update rows with missing 'Image Url'
        for row in data:
            while len(row) < len(headers):
                row.append("")
            # Ensure the row has enough columns
            if not row[image_url_index]:
                try:
                    image_url = self.get_image_url(row) 
                    if image_url:
                        image_urls.append(image_url)
                        row[image_url_index] = image_url
                except Exception as e:
                    print(f"Error generating image URL for {row} : {e}")

        # Update the Google Sheet with the new data
        body = {
            'values': [headers] + data
        }

        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption="RAW",
            body=body
        ).execute()

        return image_urls
    
    def get_image_url(self, row: list[str]) -> str:
        query = ""
        for value in row:
            query += value + " "

        urls = search_image_urls(query)
        return urls[0] if len(urls) > 0 else ""