from app.config.settings import get_settings
from typing import Dict, Any
from app.service.caching_service import CachingService
from fastapi import UploadFile
from typing import List
from zoneinfo import ZoneInfo
from PyPDF2 import PdfReader
import datetime
import json
import boto3
import os
import io
import uuid


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

        # caching
        self.caching_service = CachingService()


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
         
         
    async def create_text_file_and_save(self, content: str, case_id: str):
        try:
            random_id = str(uuid.uuid4())
            s3_key = f"{case_id}/text_input{random_id}.txt"
            self.s3_client.put_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key,
                Body=content.encode("utf-8")
            )
            return {"success": True, "s3_key": s3_key}

        except Exception as e:
            return {"error": str(e)}
        
    
    async def save_files(self, files: List[UploadFile], case_id: str):
        try:
            saved_keys = []
            now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
            timestamp = now.strftime("%Y%m%dT%H%M%S")
            for file_info in files:
                await file_info.seek(0)  # Reset pointer before reading
                content = await file_info.read()
                base, ext = os.path.splitext(file_info.filename or "")
                new_filename = f"{case_id}/{base}_{timestamp}{ext}"
                s3_key = new_filename

                if content:
                    self.s3_client.upload_fileobj(
                        io.BytesIO(content),
                        self.aws_bucket_name,
                        s3_key
                    )
                    saved_keys.append(s3_key)

                    # Cache PDF text on first upload
                    if ext.lower() == ".pdf":
                        try:
                            reader = PdfReader(io.BytesIO(content))
                            text = ""
                            for page in reader.pages:
                                text += page.extract_text() or ""
                            if text:
                                self.caching_service.set_str(f"pdf:text:{s3_key}", text, ttl_seconds=86400)
                        except Exception:
                            pass
                else:
                    print(f"Warning: {file_info.filename} is empty and will not be uploaded.")
            return {"success": True, "s3_keys": saved_keys}
        except Exception as e:
            return {"error": str(e)}
        
    
    async def save_respose_v2(self, response, case_id: str) -> str:
        try:
            now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
            timestamp = now.strftime("%Y%m%dT%H%M%S")
            if response:
                # Convert dict to JSON string if needed
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)
                s3_key = f"{case_id}/response_{timestamp}.json"
                self.s3_client.put_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key,
                    Body=response.encode("utf-8")
                )

            return {"success": True, "s3_key": s3_key}
        except Exception as e:
            return {"error": str(e)}
        

    async def extract_content(self, s3_key: str) -> Any:
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


    async def extract_pdf_text_cached_from_s3(self, s3_key: str, ttl_seconds: int = 86400) -> str:
        """
        Returns extracted text for a PDF stored at s3_key.
        Caches the result in Redis: pdf:text:{s3_key}
        """
        try:
            cache_key = f"pdf:text:{s3_key}"
            cached = self.caching_service.get_str(cache_key)
            if isinstance(cached, str) and cached != "":
                return cached

            # cached miss
            pdf_bytes = io.BytesIO()
            self.s3_client.download_fileobj(self.aws_bucket_name, s3_key, pdf_bytes)
            pdf_bytes.seek(0)

            text = ""
            try:
                reader = PdfReader(pdf_bytes)
                for page in reader.pages:
                    text += page.extract_text() or ""
            except Exception:
                # if parsing fails, return empty string (don't cache failures)
                return ""

            # cache extracted text
            self.caching_service.set_str(cache_key, text, ttl_seconds=ttl_seconds)
            return text
        except Exception:
            return ""


    async def save_files_from_bytes(self, items: List[Dict[str, Any]], case_id: str):
            """
            Save already-read files to S3.
            items: [{"filename": str, "content": bytes}, ...]
            Returns: {"success": True, "s3_keys": [str, ...]} or {"error": "..."}
            """
            try:
                if not items:
                    return {"success": True, "s3_keys": []}

                tz = ZoneInfo("America/Los_Angeles")
                ts = datetime.datetime.now(tz).strftime("%Y%m%dT%H%M%S")
                saved_keys: List[str] = []

                for it in items:
                    filename = (it.get("filename") or "").strip()
                    content = it.get("content")
                    if not filename or not content:
                        continue

                    base, ext = os.path.splitext(filename)
                    new_name = f"{case_id}/{base}_{ts}{ext}" if base else f"upload_{ts}{ext or ''}"
                    s3_key = new_name

                    self.s3_client.put_object(
                        Bucket=self.aws_bucket_name,
                        Key=s3_key,
                        Body=content
                    )
                    saved_keys.append(s3_key)

                    # Cache PDF text on first upload (from bytes we already have)
                    if ext.lower() == ".pdf":
                        try:
                            reader = PdfReader(io.BytesIO(content))
                            text = ""
                            for page in reader.pages:
                                text += page.extract_text() or ""
                            if text:
                                self.caching_service.set_str(f"pdf:text:{s3_key}", text, ttl_seconds=86400)
                        except Exception:
                            pass

                return {"success": True, "s3_keys": saved_keys}
            except Exception as e:
                return {"error": str(e)}