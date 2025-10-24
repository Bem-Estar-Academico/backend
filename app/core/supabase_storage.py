import uuid
from datetime import datetime
from typing import Dict, Optional

import requests

from app.core.config import settings
from app.core.storage_interface import StorageInterface


class SupabaseStorageManager(StorageInterface):
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.access_key = settings.AWS_ACCESS_KEY_ID
        self.secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.region = settings.AWS_REGION

        if settings.S3_ENDPOINT_URL:
            self.project_url = settings.S3_ENDPOINT_URL.replace("/storage/v1/s3", "")
            self.storage_url = f"{self.project_url}/storage/v1"
        else:
            raise ValueError("S3_ENDPOINT_URL must be configured for Supabase Storage")

    def generate_unique_filename(self, original_filename: str) -> str:
        import re
        import unicodedata

        file_parts = original_filename.rsplit(".", 1)
        name = file_parts[0]
        extension = file_parts[1] if len(file_parts) > 1 else ""

        name = unicodedata.normalize("NFD", name)
        name = "".join(c for c in name if unicodedata.category(c) != "Mn")
        name = re.sub(r"[^a-zA-Z0-9\-_.]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")
        clean_name = name[:50] if name else "file"

        now = datetime.now()
        year_month = now.strftime("%Y/%m")
        unique_id = str(uuid.uuid4())[:8]

        if extension:
            extension = re.sub(r"[^a-zA-Z0-9]", "", extension)[:10]
            filename = f"{unique_id}_{clean_name}.{extension}"
        else:
            filename = f"{unique_id}_{clean_name}"

        return f"documents/{year_month}/{filename}"

    def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        try:
            unique_filename = self.generate_unique_filename(filename)

            upload_url = (
                f"{self.storage_url}/object/{self.bucket_name}/{unique_filename}"
            )

            headers = {
                "Authorization": f"Bearer {self.access_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            }

            response = requests.post(
                upload_url, data=file_content, headers=headers, timeout=30
            )

            if response.status_code not in [200, 201]:
                raise Exception(
                    f"Upload failed with status {response.status_code}: {response.text}"
                )

            return unique_filename

        except requests.RequestException as e:
            raise Exception(f"Error uploading file to Supabase Storage: {str(e)}")

    def generate_signed_url(self, file_key: str, expiration: int = 3600) -> str:
        try:
            clean_file_key = file_key.lstrip("/")

            sign_url = (
                f"{self.storage_url}/object/sign/{self.bucket_name}/{clean_file_key}"
            )

            headers = {
                "Authorization": f"Bearer {self.access_key}",
                "Content-Type": "application/json",
            }

            payload = {"expiresIn": expiration}

            response = requests.post(
                sign_url, json=payload, headers=headers, timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if "signedURL" in result:
                    return result["signedURL"]

            return (
                f"{self.storage_url}/object/public/{self.bucket_name}/{clean_file_key}"
            )

        except requests.RequestException as e:
            clean_file_key = file_key.lstrip("/")
            return (
                f"{self.storage_url}/object/public/{self.bucket_name}/{clean_file_key}"
            )

    def delete_file(self, file_key: str) -> bool:
        try:
            clean_file_key = file_key.lstrip("/")
            delete_url = (
                f"{self.storage_url}/object/{self.bucket_name}/{clean_file_key}"
            )

            headers = {"Authorization": f"Bearer {self.access_key}"}

            response = requests.delete(delete_url, headers=headers, timeout=10)
            return response.status_code in [200, 204]

        except requests.RequestException:
            return False

    def verify_file_exists(self, file_key: str) -> bool:
        try:
            clean_file_key = file_key.lstrip("/")
            info_url = f"{self.storage_url}/object/info/public/{self.bucket_name}/{clean_file_key}"

            response = requests.get(info_url, timeout=10)
            return response.status_code == 200

        except requests.RequestException:
            return False

    def get_file_info(self, file_key: str) -> Optional[Dict]:
        try:
            clean_file_key = file_key.lstrip("/")
            info_url = f"{self.storage_url}/object/info/public/{self.bucket_name}/{clean_file_key}"

            response = requests.get(info_url, timeout=10)

            if response.status_code == 200:
                return response.json()

            return None

        except requests.RequestException:
            return None

    def generate_presigned_download_url(
        self, file_key: str, expiration: int = 3600
    ) -> str:
        return self.generate_signed_url(file_key, expiration)


supabase_storage = SupabaseStorageManager()
