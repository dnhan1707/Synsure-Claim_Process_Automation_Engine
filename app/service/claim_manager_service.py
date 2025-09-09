import logging
from app.service.supabase_service import SupabaseService
from app.schema.schema import CaseStatus
from fastapi import UploadFile, File, Form
from typing import List
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
        