from app.config.settings import get_settings
from typing import Dict, Any, List
from app.service.caching_service import CachingService
from fastapi import UploadFile
from zoneinfo import ZoneInfo
from PyPDF2 import PdfReader
import datetime
import json
import boto3
import os
import io
import uuid


class FileService:
    def __init__(self):
        s3_setting = get_settings().s3
        self.s3_client = boto3.client(
            service_name=s3_setting.service_name,
            aws_access_key_id=s3_setting.aws_access_key_id,
            aws_secret_access_key=s3_setting.aws_secret_access_key,
            region_name=s3_setting.region_name
        )
        self.aws_bucket_name = s3_setting.bucket_name
        self.caching_service = CachingService()


    async def extract_text(self, file_contents: List[Dict[str, Any]]) -> str:
        try:
            file_texts = []
            for file_info in file_contents:
                content = file_info["content"]
                reader = PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                file_texts.append(text)
            return "".join(file_texts)
        except Exception as e:
            return f"Error extracting text: {e}"


    async def create_text_file_and_save(self, content: str, case_id: str) -> Dict[str, Any]:
        try:
            s3_key = await self._generate_s3_key(case_id, '', 'text') 
            self.s3_client.put_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key,
                Body=content.encode("utf-8")
            )
            return {"success": True, "s3_key": s3_key}
        except Exception as e:
            return {"error": str(e)}


    async def save_files(self, files: List[UploadFile], case_id: str) -> Dict[str, Any]:
        try:
            if not files:
                return {"success": True, "s3_keys": []}

            saved_keys = []
            timestamp = await self._generate_timestamp()
            
            for file_info in files:
                await file_info.seek(0)
                content = await file_info.read()
                
                if not content:
                    print(f"Warning: {file_info.filename} is empty and will not be uploaded.")
                    continue

                s3_key = await self._generate_file_s3_key(case_id, file_info.filename or "", timestamp)
                
                # Upload to S3
                self.s3_client.upload_fileobj(
                    io.BytesIO(content),
                    self.aws_bucket_name,
                    s3_key
                )
                saved_keys.append(s3_key)

                # Cache PDF text if applicable
                await self._cache_pdf(content, s3_key)

            return {"success": True, "s3_keys": saved_keys}
        except Exception as e:
            return {"error": str(e)}


    async def save_respose_v2(self, response, case_id: str) -> Dict[str, Any]:
        try:
            if not response:
                return {"error": "Empty response provided"}

            # Convert to JSON string if needed
            response_str = await self._prepare_response_content(response)
            s3_key = await self._generate_s3_key(case_id, '', 'response')

            self.s3_client.put_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key,
                Body=response_str.encode("utf-8")
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
            return json.loads(content)
        except Exception as e:
            return {"error": str(e)}


    async def extract_pdf_text_cached_from_s3(self, s3_key: str, ttl_seconds: int = 86400) -> str:
        try:
            cache_key = f"pdf:text:{s3_key}"
            
            cached = await self.caching_service.get_str(cache_key)
            if isinstance(cached, str) and cached:
                return cached

            # Cache miss - download and extract
            text = await self._extract_pdf_text_from_s3(s3_key)
            if text:
                await self.caching_service.set_str(cache_key, text, ttl_seconds=ttl_seconds)
            
            return text
        except Exception as e:
            return ""


    async def save_files_from_bytes(self, items: List[Dict[str, Any]], case_id: str) -> Dict[str, Any]:
        try:
            if not items:
                return {"success": True, "s3_keys": []}

            timestamp = await self._generate_timestamp()
            saved_keys: List[str] = []

            for item in items:
                filename = (item.get("filename") or "").strip()
                content = item.get("content")
                
                if not filename or not content:
                    continue

                s3_key = await self._generate_file_s3_key(case_id, filename, timestamp)

                self.s3_client.put_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key,
                    Body=content
                )
                saved_keys.append(s3_key)

                # Cache PDF text if applicable
                await self._cache_pdf(content, s3_key)

            return {"success": True, "s3_keys": saved_keys}
        except Exception as e:
            return {"error": str(e)}

# -------------------------------------------------------- Helper ------------------------------------------
    async def _generate_timestamp(self) -> str:
        """Generate timestamp string for file naming."""
        now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
        return now.strftime("%Y%m%dT%H%M%S")


    async def _generate_s3_key(self, case_id: str, filename: str, file_type: str = "file") -> str:
        """Generate S3 key based on file type."""
        if file_type == "text":
            random_id = str(uuid.uuid4())
            return f"{case_id}/text_input{random_id}.txt"
        elif file_type == "response":
            timestamp = await self._generate_timestamp()
            return f"{case_id}/response_{timestamp}.json"
        else:
            timestamp = await self._generate_timestamp()
            base, ext = os.path.splitext(filename or "")
            return f"{case_id}/{base}_{timestamp}{ext}" if base else f"upload_{timestamp}{ext or ''}"


    async def _generate_file_s3_key(self, case_id: str, filename: str, timestamp: str) -> str:
        """Generate S3 key for uploaded files with timestamp."""
        base, ext = os.path.splitext(filename)
        return f"{case_id}/{base}_{timestamp}{ext}" if base else f"upload_{timestamp}{ext or ''}"


    async def _prepare_response_content(self, response) -> str:
        """Convert response to JSON string if needed."""
        if isinstance(response, str):
            return response
        return json.dumps(response, ensure_ascii=False)


    async def _cache_pdf(self, content: bytes, s3_key: str) -> None:
        """Extract PDF text and cache it."""
        try:
            if not s3_key.lower().endswith('.pdf'):
                return

            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            
            if text:
                await self.caching_service.set_str(f"pdf:text:{s3_key}", text, ttl_seconds=86400)
        except Exception as e:
            print(f"Error in _cache_pdf: {e}")
            pass


    async def _extract_pdf_text_from_s3(self, s3_key: str) -> str:
        """Extract text from PDF stored in S3."""
        try:
            pdf_bytes = io.BytesIO()
            self.s3_client.download_fileobj(self.aws_bucket_name, s3_key, pdf_bytes)
            pdf_bytes.seek(0)

            reader = PdfReader(pdf_bytes)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception:
            return ""