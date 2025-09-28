from app.config.settings import get_settings
from fastapi import UploadFile
import boto3
import logging
import asyncio
import json
import io
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        setting = get_settings()
        s3_setting = setting.s3
        self.s3_client = boto3.client(
            service_name=s3_setting.service_name,
            aws_access_key_id=s3_setting.aws_access_key_id,
            aws_secret_access_key=s3_setting.aws_secret_access_key,
            region_name=s3_setting.region_name
        )
        if setting.env and setting.env.lower() == "development":
            self.aws_bucket_name = s3_setting.bucket_name_development or s3_setting.bucket_name
        else: 
            self.aws_bucket_name = s3_setting.bucket_name


    async def generate_accessible_link(self, s3_key: str) -> str:
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.aws_bucket_name, "Key": s3_key}
                )
            )
        except Exception as e:
            logger.error(f"Error generate_accessible_link: {e}")
            return ""
    
    async def extract_text(self, file_contents: list[dict[str, any]]) -> str:
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

    async def save_with_key(self, file: UploadFile, s3_key: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.upload_fileobj(
                    Fileobj=file.file,
                    Bucket=self.aws_bucket_name,
                    Key=s3_key
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error save_with_key: {e}")
            return False


    async def save_response_json(self, tenant_id: str, case_id: str, new_response_file_id: str, data: dict) -> str | None:
        """
        Save a response dict as a JSON file in S3.

        Args:
            tenant_id (str): Tenant ID
            case_id (str): Case ID
            new_response_file_id (str): Unique response file ID
            data (dict): Dictionary to be saved as JSON

        Returns:
            str | None: S3 key of the saved file, or None if failed
        """
        try:
            response_file_key = f"{tenant_id}/{case_id}/responses/{new_response_file_id}_response.json"

            # Convert dict → JSON → bytes
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            file_obj = io.BytesIO(json_bytes)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.upload_fileobj(
                    Fileobj=file_obj,
                    Bucket=self.aws_bucket_name,
                    Key=response_file_key,
                    ExtraArgs={"ContentType": "application/json"}
                )
            )

            return response_file_key
        except Exception as e:
            logger.error(f"Error save_response_json: {e}")
            return None


    async def overwrite_file(self, file: UploadFile, s3_key: str):
        try:
            file_bytes = await file.read()

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key,
                    Body=file_bytes,
                    ContentType=file.content_type
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error overwrite_file: {e}")
            return False
        

    async def get_file_content_by_key(self, s3_key: str) -> str:
        try:
            def _get_pdf_text():
                response = self.s3_client.get_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key
                )
                file_bytes = response["Body"].read()

                if not file_bytes:
                    raise ValueError(f"S3 returned empty content for key={s3_key}")

                # Read PDF from memory
                pdf_stream = io.BytesIO(file_bytes)
                reader = PdfReader(pdf_stream)

                text_content = []
                for i, page in enumerate(reader.pages):
                    try:
                        text_content.append(page.extract_text() or "")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {i} of {s3_key}: {e}")
                        continue

                return "\n".join(text_content).strip()

            pdf_text = await asyncio.to_thread(_get_pdf_text)
            return pdf_text

        except Exception as e:
            logger.error(f"Error get_file_content_by_key for {s3_key}: {e}")
            return ""

    async def get_file_raw_bytes(self, s3_key: str) -> bytes:
        """Get raw file bytes from S3."""
        try:
            def _get_bytes():
                response = self.s3_client.get_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key
                )
                return response["Body"].read()
            
            return await asyncio.to_thread(_get_bytes)
        except Exception as e:
            logger.error(f"Error getting raw bytes from S3 {s3_key}: {e}")
            return b""
    

    async def get_response_file_data(self, s3_key: str) -> dict:
        """
        Get response JSON data from S3.
        
        Args:
            s3_key (str): S3 key of the response JSON file
            
        Returns:
            dict: Parsed JSON data from S3, or empty dict if failed
        """
        try:
            logger.info(f"Getting response file data from S3 key: {s3_key}")
            
            def _get_response_json():
                response = self.s3_client.get_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key
                )
                file_bytes = response["Body"].read()

                if not file_bytes:
                    raise ValueError(f"S3 returned empty content for key={s3_key}")

                # Parse JSON from bytes
                json_content = file_bytes.decode('utf-8')
                return json.loads(json_content)

            response_data = await asyncio.to_thread(_get_response_json)
            
            logger.info(f"Successfully retrieved response data from S3: {s3_key}")
            return response_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in S3 file {s3_key}: {e}")
            return {"error": f"Invalid JSON format: {str(e)}"}
        except Exception as e:
            logger.error(f"Error getting response file data from {s3_key}: {e}", exc_info=True)
            return {"error": str(e)}
            
