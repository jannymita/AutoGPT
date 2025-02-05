import os
import hashlib
import json
import base64
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField
class JsonToSpreadsheetBlock(Block):
    scopes: list[str] = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    class Input(BlockSchema):
        json_content: str = SchemaField(
            description="The content of the JSON to write",
        )
        spreadsheet_id: Optional[str] = SchemaField(
            description="The ID of the spreadsheet to override instead of creating a new one",
            default=None
        )

    class Output(BlockSchema):
        spreadsheet_link: str = SchemaField(
            description="The link to the created spreadsheet"
        )
        spreadsheet_id: str = SchemaField(
            description="The ID of the created spreadsheet"
        )

    def __init__(self):
        super().__init__(
            id="492bbb58-14b1-447f-b49b-25a3c768e11d",  # Replace this with a new unique ID
            description="This block writes Shopify product json to a Google Sheets spreadsheet.",
            categories={BlockCategory.DATA},
            input_schema=JsonToSpreadsheetBlock.Input,
            output_schema=JsonToSpreadsheetBlock.Output,
            test_input={
                "json_content": "[{\"username\":\"Alice\",\"email\":\"alice@example.com\",\"age\":30},{\"username\":\"Bob\",\"email\":\"bob@example.com\",\"age\":25}]",
            },
            test_output={
                "spreadsheet_link": "https://docs.google.com/spreadsheets/d/0f0bdc30-9606-4691-aa2d-807605b33b63",
                "spreadsheet_id": "95d29dd9-cb29-42fa-8632-058270978e21"
            }
        )
    
    def json_excute(self, json_content: str, spreadsheet_id: str = None) -> dict:
        sa_base64 = os.getenv("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT")
        if not sa_base64:
            raise Exception("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT is not set")

        # Decode the base64 service account key
        sa_json = base64.b64decode(sa_base64).decode('utf-8')
        service_account_info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, 
            scopes=JsonToSpreadsheetBlock.scopes
        )

        # Initialize the Google Sheets and Drive APIs
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()
        drive_service = build("drive", "v3", credentials=credentials)

        file_name = hashlib.md5(json_content.encode()).hexdigest()
        # Create a new spreadsheet or use the provided one
        if spreadsheet_id:
            spreadsheet = sheet.get(
                spreadsheetId=spreadsheet_id
            ).execute()
        else:
            spreadsheet_body = {
                "properties": {"title": file_name}
            }

            spreadsheet = sheet.create(
                body=spreadsheet_body, 
                fields="spreadsheetId"
            ).execute()
            spreadsheet_id = spreadsheet.get("spreadsheetId")

        # Parse the JSON content using json.loads
        data = json.loads(json_content)

        # Convert the JSON data to a Google Sheets compatible format
        body = {
            "values": [[key for key in data[0]]] + [[row[key] for key in row] for row in data]
        }

        # Update the spreadsheet with parsed data
        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",  # Starting from the first row and column
            valueInputOption="RAW",
            body=body
        ).execute()

        # Make the file public
        self.make_file_public(spreadsheet_id, drive_service)

        # Construct the spreadsheet link
        spreadsheet_link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        return {
            "spreadsheet_link": spreadsheet_link,
            "spreadsheet_id": spreadsheet_id
        }
    
    def make_file_public(self, spreadsheet_id: str, drive_service):
        permission_body = {
            "type": "anyone",  # Make it accessible to anyone with the link
            "role": "writer"   # Use "writer" if you want others to edit the file
        }
        
        # Set the file permissions using the Drive API
        drive_service.permissions().create(
            fileId=spreadsheet_id,  # The ID of the file to make public
            body=permission_body
        ).execute()

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            if not input_data.json_content:
                raise ValueError("JSON content is required")

            # Call the json_execute method and get the result
            result = self.json_excute(input_data.json_content, input_data.spreadsheet_id)
            spreadsheet_link = result["spreadsheet_link"]
            spreadsheet_id = result["spreadsheet_id"]

            yield "spreadsheet_link", spreadsheet_link
            yield "spreadsheet_id", spreadsheet_id
        except Exception as e:
            yield "error", f"An error occurred: {e}"

