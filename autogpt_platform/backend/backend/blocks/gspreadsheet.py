import os
from typing import Any
import base64
import json
import re
import json
import csv
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build

from backend.data.block import Block, BlockCategory, BlockOutput, BlockSchema
from backend.data.model import SchemaField

class GSpreadsheetBlock(Block):
    scopes: list[str] = ["https://www.googleapis.com/auth/spreadsheets"]

    class Input(BlockSchema):
        spreadsheet_id: str = SchemaField(
            description="The ID of the spreadsheet to write to",
        )
        range: str = SchemaField(
            description="The A1 notation of the range to write",
            default="sheet1!A1:Z100"
        )

    class Output(BlockSchema):
        data: list[dict[str, Any]] = SchemaField(description="Status of the email sending operation")
        error: str = SchemaField(
            description="Error message if reading the spreadsheet failed"
        )

    def __init__(self):
        super().__init__(
            id="9a824887-05a7-401d-8602-718fe283bd1e",
            description="This block reads data from a Google Sheets spreadsheet.",
            categories={BlockCategory.DATA},
            input_schema=GSpreadsheetBlock.Input,
            output_schema=GSpreadsheetBlock.Output,
            test_input={
                "spreadsheet_id": "1lb877lBEbTuuHytD75VWVCunkCGU_DdFwTbsNU0yi1Y",
                "range": "Sheet1!A1:AL101",
            },
            test_output=[("data", [])],
            test_mock={"read_spreadsheet": lambda *args, **kwargs: "OK"},
        )

    @staticmethod
    def extract_spreadsheet_id(spreadsheet_source: str) -> str:
        pattern = r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)/"
        match = re.search(pattern, spreadsheet_source)
        if match:
            return match.group(1)
        return spreadsheet_source
    
    @staticmethod
    def read_spreadsheet(spreadsheet_id: str, range: str) -> list[list[str]]:
        sa_base64 = os.getenv("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT")
        if not sa_base64:
            raise Exception("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT is not set")

        # Decode the base64 service account key
        sa_json = base64.b64decode(sa_base64).decode('utf-8')
        service_account_info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, 
            scopes=GSpreadsheetBlock.scopes
        )

        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()

        result = sheet.values().get(spreadsheetId=GSpreadsheetBlock.parse_spreadsheet_source(spreadsheet_id), range=range).execute()
        return result.get("values", [])
    
    @staticmethod 
    def parse_spreadsheet_source(spreadsheet_source: str) -> str:
        pattern = r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, spreadsheet_source)
        if match:
            return match.group(1)
        return spreadsheet_source

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            spreadsheet_id = self.extract_spreadsheet_id(input_data.spreadsheet_id)
            data = self.read_spreadsheet(spreadsheet_id, input_data.range)
            output_data = []
            if data:
                headers = data[0]
                for row in data[1:]:
                    output_data.append({headers[i]: value for i, value in enumerate(row)})
            yield "data", output_data
        except Exception as e:
            yield "error", f"An error occurred: {e}"  

class GSpreadsheetGenerationBlock(Block):
    scopes: list[str] = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file"]

    class Input(BlockSchema):
        csv_text: str = SchemaField(
            description="CSV formatted text where the first row is the header.",
        )

    class Output(BlockSchema):
        spreadsheet_url: str = SchemaField(description="URL of the created spreadsheet")
        error: str = SchemaField(
            description="Error message if spreadsheet creation failed"
        )

    def __init__(self):
        super().__init__(
            id="1a2b3c4d-5678-90ab-cdef-1234567890ab",
            description="This block generates a Google Sheet from CSV text and makes it publicly accessible.",
            categories={BlockCategory.DATA},
            input_schema=GSpreadsheetGenerationBlock.Input,
            output_schema=GSpreadsheetGenerationBlock.Output,
            test_input={
                "csv_text": "Name, Age, Country\nJohn, 25, USA\nAlice, 30, Canada\nBob, 22, UK"
            },
            test_output=[("spreadsheet_url", ""), ("error", "")],
        )

    @staticmethod
    def create_public_spreadsheet_from_csv(csv_text: str) -> str:
        sa_base64 = os.getenv("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT")
        if not sa_base64:
            raise Exception("GOOGLE_SPREADSHEET_SERVICE_ACCOUNT is not set")

        sa_json = base64.b64decode(sa_base64).decode("utf-8")
        service_account_info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=GSpreadsheetGenerationBlock.scopes,
        )

        service = build("sheets", "v4", credentials=credentials)
        drive_service = build("drive", "v3", credentials=credentials)

        spreadsheet = service.spreadsheets().create(
            body={"properties": {"title": "New Public Spreadsheet"}}
        ).execute()

        spreadsheet_id = spreadsheet["spreadsheetId"]
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        csv_reader = csv.reader(io.StringIO(csv_text))
        data = [row for row in csv_reader]

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": data}
        ).execute()

        drive_service.permissions().create(
            fileId=spreadsheet_id,
            # body={"type": "anyone", "role": "reader"},
            body={"type": "anyone", "role": "writer"},
        ).execute()

        return spreadsheet_url

    def run(self, input_data: Input, **kwargs) -> BlockOutput:
        try:
            spreadsheet_url = self.create_public_spreadsheet_from_csv(input_data.csv_text)
            yield "spreadsheet_url", spreadsheet_url
        except Exception as e:
            yield "error", f"An error occurred: {e}"
