from typing import List
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import datetime
import json
import boto3
import os
import io

load_dotenv()

class FileService():
    def __init__(self):
        self.s3_client = boto3.client(
            service_name='s3',
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION")
        )
        self.AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME")


    async def save(self, case_id: str, case_name: str, file_contents: list, texts: str):
        try:
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            if len(file_contents) >= 1:
                for file_info in file_contents:
                    original_filename = file_info["filename"]
                    name, ext = os.path.splitext(original_filename)
                    new_filename = f"{name}_{timestamp}{ext}"  # Correct format
                    s3_key = f"{case_id}/{new_filename}"

                    self.s3_client.upload_fileobj(
                        io.BytesIO(file_info["content"]),
                        self.AWS_BUCKET_NAME,
                        s3_key
                    )
            if texts is not None and texts != "":
                s3_key = f"{case_id}/texts_{timestamp}.txt"
                self.s3_client.put_object(
                    Bucket=self.AWS_BUCKET_NAME,
                    Key=s3_key,
                    Body=texts.encode("utf-8")
                )

            if case_name or case_name != "":
                # print("saving name")
                s3_key = f"{case_id}/case_name.txt"
                self.s3_client.put_object(
                    Bucket=self.AWS_BUCKET_NAME,
                    Key=s3_key,
                    Body=case_name.encode("utf-8")
                )

            return None

        except Exception as e:
            return {"error": e}
    
    async def save_response(self, case_id: str, response):
        try:
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            if response:
                # Convert dict to JSON string if needed
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)
                s3_key = f"{case_id}/response_{timestamp}.json"
                self.s3_client.put_object(
                    Bucket=self.AWS_BUCKET_NAME,
                    Key=s3_key,
                    Body=response.encode("utf-8")
                )
            return None
        except Exception as e:
            return {"error": e}
        

    async def get_case_data(self, case_id: str):
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.AWS_BUCKET_NAME,
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
                        self.s3_client.download_fileobj(self.AWS_BUCKET_NAME, key, pdf_bytes)
                        pdf_bytes.seek(0)
                        files.append({
                            "filename": filename,
                            "content": pdf_bytes.getvalue()
                        })

                    # Handle manual text file
                    elif filename.lower().startswith("texts_") and filename.lower().endswith(".txt"):
                        s3_obj = self.s3_client.get_object(
                            Bucket=self.AWS_BUCKET_NAME,
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
                Bucket=self.AWS_BUCKET_NAME,
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
                            Params={'Bucket': self.AWS_BUCKET_NAME, 'Key': key},
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
                Bucket=self.AWS_BUCKET_NAME,
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
                        Bucket=self.AWS_BUCKET_NAME,
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
                    Bucket=self.AWS_BUCKET_NAME,
                    Prefix=f"{case_id}/"
                )
                if "Contents" in response:
                    all_keys.extend([{"Key": obj["Key"]} for obj in response["Contents"]])
            # Delete in batches of 1000
            for i in range(0, len(all_keys), 1000):
                self.s3_client.delete_objects(
                    Bucket=self.AWS_BUCKET_NAME,
                    Delete={"Objects": all_keys[i:i+1000]}
                )
            return {"success": True, "deleted_keys": len(all_keys)}
        except Exception as e:
            return {"error": str(e)}
        
    
    async def update_case_name(self, case_id: str, case_name: str):
        try:
            s3_key = f"{case_id}/case_name.txt"
            self.s3_client.put_object(
                Bucket=self.AWS_BUCKET_NAME,
                Key=s3_key,
                Body=case_name.encode("utf-8")
            )
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
