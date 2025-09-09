import logging
from app.service.supabase_service import SupabaseService
from app.schema.schema import CaseStatus
from fastapi import UploadFile, File, Form
from typing import List, Dict, Any
import uuid
import boto3
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

class ClaimManagerService:
    def __init__(self):
        self.sp_service = SupabaseService()
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


    async def create_empty_claim(
        self, 
        tenant_id: str, 
        name: str, 
        status: CaseStatus = CaseStatus.open
    ) -> bool:
        try:
            res = await self.sp_service.insert(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "case_name": name
                }
            )

            if not res:
                logger.warning("Failed to insert case for tenant_id: %s, case_name: %s", tenant_id, name)
                return False
            
            logger.info("Successfully created empty claim for tenant_id: %s, case_name: %s", tenant_id, name)
            return True

        except Exception as e:
            logger.error("Claim Manager Service Error - create_empty_claim for tenant_id: %s, case_name: %s - %s", 
                        tenant_id, name, str(e), exc_info=True)
            return False
        
    
    async def create_claim(
        self,
        tenant_id: str,
        name: str,
        files: List[UploadFile] = File(None),
        status: CaseStatus = CaseStatus.open
    ) -> bool:
        
        try:
            res = await self.sp_service.insert(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "case_name": name
                }
            )

            if not res:
                logger.warning("Failed to insert case for tenant_id: %s, case_name: %s", tenant_id, name)
                return False
            
            case_id = res["id"]

            if files:
                for file in files:
                    file_id = str(uuid.uuid4())
                    s3_key = f"{tenant_id}/{case_id}/uploads/{file_id}_{file.filename}"

                    # upload on S3
                    self.s3_client.upload_fileobj(file.file, self.aws_bucket_name, s3_key)

                    # insert into DB
                    insert_res = await self.sp_service.insert(
                        table_name="files",
                        object={
                            "id": file_id,
                            "tenant_id": tenant_id,
                            "case_id": case_id,
                            "kind": "raw_upload",
                            "name": file.filename,
                            "s3_bucket": self.aws_bucket_name,
                            "s3_key": s3_key,
                        }
                    )
                    if not insert_res:
                        logger.warning("No files was inserted")
                        return False

                    logger.info("Uploaded file %s to S3 and inserted into DB", file.filename)


            logger.info("Successfully created empty claim for tenant_id: %s, case_name: %s", tenant_id, name)
            return True

        except Exception as e:
            logger.error("Claim Manager Service Error - create_empty_claim for tenant_id: %s, case_name: %s - %s", 
                        tenant_id, name, str(e), exc_info=True)
            return False
        

    async def get_claim_by_id(self, id: str) -> Dict[str, Any]:
        try:
            general_data = await self.sp_service.get_row_by_id(
                id=id,
                table_name="cases",
                columns="id, tenant_id, case_name, status"
            )
            if not general_data:
                logger.warning("No case found with id: %s", id)
                return {}
            
            tenant_id = general_data["tenant_id"]

            related_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=id,
                tenant_id=tenant_id,
                columns="id, name, kind, s3_bucket, s3_key, uploaded_at"
            )
            files_with_urls = []
            if related_files:
                for file in related_files:
                    try:
                        presigned_url = self.s3_client.generate_presigned_url(
                            "get_object",
                            Params={
                                "Bucket": file["s3_bucket"],
                                "Key": file["s3_key"]
                            },
                            ExpiresIn=900
                        )
                        files_with_urls.append({
                            "id": file["id"],
                            "name": file["name"],
                            "kind": file["kind"],
                            "uploaded_at": file["uploaded_at"],
                            "download_url": presigned_url
                        })

                    except Exception as e:
                        logger.error("Could not generate presigned URL for file %s: %s", file["id"], str(e))

            return {
                "id": general_data["id"],
                "case_name": general_data["case_name"],
                "status": general_data["status"],
                "files": files_with_urls   
                }   

        except Exception as e:
            logger.error("Error get_claim_by_id")
            return {}


    async def get_all_claim(self) -> List[Dict[str, Any]]:
        try:
            res = await self.sp_service.get_all(
                table_name="cases",
                columns="id, tenant_id, case_name, status"
            )
            if not res:
                logger.error("Error get_all_claim either empty or None")
                return []

            return res

        except Exception as e:
            logger.error("Error get_all_claim")
            return []
