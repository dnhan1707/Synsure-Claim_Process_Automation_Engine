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


    async def save(self, case_id: str, case_name: str, file_contents: list, texts: str):
        try:
            now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
            timestamp = now.strftime("%Y%m%dT%H%M%S")
            if len(file_contents) >= 1:
                for file_info in file_contents:
                    original_filename = file_info["filename"]
                    name, ext = os.path.splitext(original_filename)
                    new_filename = f"{name}_{timestamp}{ext}"  # Correct format
                    s3_key = f"{case_id}/{new_filename}"

                    self.s3_client.upload_fileobj(
                        io.BytesIO(file_info["content"]),
                        self.aws_bucket_name,
                        s3_key
                    )
            if texts is not None and texts != "":
                s3_key = f"{case_id}/texts_{timestamp}.txt"
                self.s3_client.put_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key,
                    Body=texts.encode("utf-8")
                )

            if case_name or case_name != "":
                # print("saving name")
                s3_key = f"{case_id}/case_name.txt"
                self.s3_client.put_object(
                    Bucket=self.aws_bucket_name,
                    Key=s3_key,
                    Body=case_name.encode("utf-8")
                )

            return None

        except Exception as e:
            return {"error": e}
    
    async def save_response(self, case_id: str, response):
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
            return None
        except Exception as e:
            return {"error": e}
        

    async def get_case_data(self, case_id: str):
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.aws_bucket_name,
                Prefix=f"{case_id}/"
            )

            files = []
            manual_text = ""

            if "Contents" in response:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    filename = key.split("/")[-1]

                    # Only match .pdf at the end
                    if filename.lower().endswith(".pdf"):
                        pdf_bytes = io.BytesIO()
                        self.s3_client.download_fileobj(self.aws_bucket_name, key, pdf_bytes)
                        pdf_bytes.seek(0)
                        files.append({
                            "filename": filename,
                            "content": pdf_bytes.getvalue()
                        })

                    # Handle manual text file
                    elif filename.lower().startswith("texts_") and filename.lower().endswith(".txt"):
                        s3_obj = self.s3_client.get_object(
                            Bucket=self.aws_bucket_name,
                            Key=key
                        )
                        manual_text = s3_obj["Body"].read().decode("utf-8")

            return files, manual_text

        except Exception as e:
            # Optional: log the error here
            return [], ""
    
    async def get_case_files_links(self, case_id: str, expires_in: int = 3600):
        """
        Returns a list of dicts: [{filename, url, type}]
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.aws_bucket_name,
                Prefix=f"{case_id}/"
            )
            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    filename = key.split("/")[-1]
                    if filename:  # skip folder itself
                        url = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': self.aws_bucket_name, 'Key': key},
                            ExpiresIn=expires_in
                        )
                        file_type = "pdf" if ".pdf" in filename.lower() else "text" if filename.lower().endswith(".txt") else "other"
                        files.append({
                            "filename": filename,
                            "url": url,
                            "type": file_type
                        })
            return files
        except Exception as e:
            return []


    async def get_cases_info(self):
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.aws_bucket_name,
                Prefix="",
                Delimiter="/"
            )

            # Folders are listed here, not in "Contents"
            prefixes = response.get("CommonPrefixes", [])
            case_ids = [prefix["Prefix"].rstrip("/") for prefix in prefixes]

            cases = []
            for case_id in case_ids:
                case_name = ""
                try:
                    s3_obj = self.s3_client.get_object(
                        Bucket=self.aws_bucket_name,
                        Key=f"{case_id}/case_name.txt"
                    )
                    case_name = s3_obj["Body"].read().decode("utf-8")
                except Exception:
                    pass  # Skip if case_name.txt doesn't exist

                cases.append({"id": case_id, "case_name": case_name})
            
            return cases

        except Exception as e:
            # print("S3 Error:", e)
            return []


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
        
    
    async def delete_cases(self, case_ids: List[str]):
        try:
            all_keys = []
            for case_id in case_ids:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.aws_bucket_name,
                    Prefix=f"{case_id}/"
                )
                if "Contents" in response:
                    all_keys.extend([{"Key": obj["Key"]} for obj in response["Contents"]])
            # Delete in batches of 1000
            for i in range(0, len(all_keys), 1000):
                self.s3_client.delete_objects(
                    Bucket=self.aws_bucket_name,
                    Delete={"Objects": all_keys[i:i+1000]}
                )
            return {"success": True, "deleted_keys": len(all_keys)}
        except Exception as e:
            return {"error": str(e)}
        
    
    async def update_case_name(self, case_id: str, case_name: str):
        try:
            s3_key = f"{case_id}/case_name.txt"
            self.s3_client.put_object(
                Bucket=self.aws_bucket_name,
                Key=s3_key,
                Body=case_name.encode("utf-8")
            )
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        
    
    async def get_latest_response(self, case_id: str):
        try:
            prefix = f"{case_id}/response_"
            response = self.s3_client.list_objects_v2(
                Bucket=self.aws_bucket_name,
                Prefix=prefix
            )
            if "Contents" not in response or not response["Contents"]:
                return {"error": "No response files found"}
            # Find the latest by sorting keys
            response_files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".json")]
            if not response_files:
                return {"error": "No response files found"}
            latest_key = sorted(response_files)[-1]
            s3_obj = self.s3_client.get_object(Bucket=self.aws_bucket_name, Key=latest_key)
            content = s3_obj["Body"].read().decode("utf-8")
            return json.loads(content)
        except Exception as e:
            return {"error": str(e)}
    

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
