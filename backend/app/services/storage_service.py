import logging
import os
from typing import Optional, Union
from uuid import UUID
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        try:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY and not settings.SUPABASE_URL.startswith("https://placeholder"):
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("StorageService: Supabase Storage client initialized.")
        except Exception as e:
            logger.error(f"StorageService: Failed to initialize Supabase client: {str(e)}")

    def upload_file(
        self,
        bucket_name: str,
        destination_path: str,
        file_bytes: Union[bytes, bytearray],
        content_type: str = "application/pdf"
    ) -> Optional[str]:
        """
        Uploads bytes to a Supabase storage bucket and returns the public URL.
        """
        if not self.client:
            self._init_client()
        if not self.client:
            logger.warning("Storage client unavailable. File not uploaded to cloud storage.")
            return None

        try:
            # Upload file bytes to the bucket
            self.client.storage.from_(bucket_name).upload(
                path=destination_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            # Retrieve public URL
            public_url = self.client.storage.from_(bucket_name).get_public_url(destination_path)
            logger.info(f"StorageService: Uploaded {destination_path} to '{bucket_name}'. URL: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"StorageService: Error uploading file to bucket '{bucket_name}': {str(e)}")
            # Fallback direct public URL format
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{destination_path}"

    def upload_document_pdf(
        self,
        user_id: Union[str, UUID],
        filename: str,
        file_bytes: Union[bytes, bytearray],
        content_type: str = "application/pdf"
    ) -> Optional[str]:
        """
        Uploads a user verification document (Aadhaar, PAN, GST, Udyam) to Supabase Storage.
        Path format: documents/{user_id}/{filename}
        """
        dest = f"{str(user_id)}/{filename}"
        return self.upload_file(bucket_name="documents", destination_path=dest, file_bytes=file_bytes, content_type=content_type)

    def upload_scheme_pdf(
        self,
        scheme_id: Union[str, UUID],
        filename: str,
        file_bytes: Union[bytes, bytearray],
        content_type: str = "application/pdf"
    ) -> Optional[str]:
        """
        Uploads an official government Scheme guideline PDF to Supabase Storage.
        Path format: schemes/{scheme_id}/{filename}
        """
        dest = f"{str(scheme_id)}/{filename}"
        return self.upload_file(bucket_name="schemes", destination_path=dest, file_bytes=file_bytes, content_type=content_type)

    def get_public_url(self, bucket_name: str, file_path: str) -> str:
        if not self.client:
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{file_path}"
        return self.client.storage.from_(bucket_name).get_public_url(file_path)

storage_service = StorageService()
