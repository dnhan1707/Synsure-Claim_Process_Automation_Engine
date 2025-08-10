from app.config.settings import get_settings
from fastapi import UploadFile
from typing import List
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from PyPDF2 import PdfReader
import datetime
import json
import boto3
import os
import io
import uuid

load_dotenv()

class FileService():
    def __init__(self):
        s3_setting = get_settings().s3
        self.s3_client = boto3.client(
            service_name=s3_setting.service_name,
            aws_access_key_id=s3_setting.aws_access_key_id,
            aws_secret_access_key=s3_setting.aws_secret_access_key,
            region_name=s3_setting.region_name
        )
        self.aws_bucket_name = s3_setting.bucket_name



    async def extract_text(self, file_contents: list) -> str:
        try:
            file_texts = []
            for file_info in file_contents:
                content = file_info["content"]
                reader = PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                file_texts.append(text)
            details = "".join(file_texts)
            return details
        except Exception as e:
            return f"Error extracting text: {e}"
         
         
    async def create_text_file_and_save(self, content: str):
        try:
            random_id = str(uuid.uuid4())
            s3_key = f"text_input{random_id}.txt"
            self.s3_client.put_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key,
                Body=content.encode("utf-8")
            )
            return {"success": True, "s3_key": s3_key}

        except Exception as e:
            return {"error": str(e)}
        
    
    async def save_files(self, files: List[UploadFile]):
        try:
            saved_keys = []
            now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
            timestamp = now.strftime("%Y%m%dT%H%M%S")
            for file_info in files:
                await file_info.seek(0)  # Reset pointer before reading
                content = await file_info.read()
                # print(f"Uploading {file_info.filename}, size: {len(content)} bytes")
                new_filename = f"{os.path.splitext(file_info.filename)[0]}_{timestamp}{os.path.splitext(file_info.filename)[1]}"
                s3_key = new_filename
                if content:
                    self.s3_client.upload_fileobj(
                        io.BytesIO(content),
                        self.aws_bucket_name,
                        s3_key
                    )
                else:
                    print(f"Warning: {file_info.filename} is empty and will not be uploaded.")
                saved_keys.append(s3_key)
            return {"success": True, "s3_keys": saved_keys}
        except Exception as e:
            return {"error": str(e)}
        
    
    async def save_respose_v2(self, response) -> str:
        try:
            now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
            timestamp = now.strftime("%Y%m%dT%H%M%S")
            if response:
                # Convert dict to JSON string if needed
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)
                s3_key = f"response_{timestamp}.json"
                self.s3_client.put_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key,
                    Body=response.encode("utf-8")
                )

            return {"success": True, "s3_key": s3_key}
        except Exception as e:
            return {"error": str(e)}
        

    async def extract_content(self, s3_key: str):
        try:
            s3_obj = self.s3_client.get_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key
            )
            content = s3_obj["Body"].read().decode("utf-8")
            content_json = json.loads(content)
            return content_json
        
        except Exception as e:
            return {"error": str(e)}
