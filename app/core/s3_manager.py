import urllib.parse
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import boto3  # type: ignore
from botocore.config import Config  # type: ignore
from botocore.exceptions import ClientError, NoCredentialsError  # type: ignore

from app.core.config import settings
from app.core.storage_interface import StorageInterface


class S3Manager(StorageInterface):
    def __init__(self):
        config = Config(signature_version="s3v4", s3={"addressing_style": "path"})

        client_args: Dict[str, Any] = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
            "config": config,
        }

        if settings.S3_ENDPOINT_URL:
            client_args["endpoint_url"] = settings.S3_ENDPOINT_URL

        self.s3_client = boto3.client("s3", **client_args)  # type: ignore
        self.bucket_name = settings.S3_BUCKET_NAME

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

            self.s3_client.put_object(  # type: ignore
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=file_content,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )

            return unique_filename

        except (ClientError, NoCredentialsError) as e:
            raise Exception(f"Error uploading file to S3: {str(e)}")

    def generate_presigned_download_url(
        self, file_key: str, expiration: int = 3600, inline: bool = True
    ) -> str:
        try:
            clean_file_key = file_key.lstrip("/")
            params = {"Bucket": self.bucket_name, "Key": clean_file_key}
            if inline:
                params["ResponseContentDisposition"] = "inline"
            url = self.s3_client.generate_presigned_url(  # type: ignore
                "get_object",
                Params=params,
                ExpiresIn=expiration,
                HttpMethod="GET",
            )

            if settings.S3_ENDPOINT_URL and "supabase" in settings.S3_ENDPOINT_URL:
                if not url or "Missing signature" in url:
                    encoded_key = urllib.parse.quote(clean_file_key, safe="/")
                    url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{encoded_key}"

            return url  # type: ignore

        except (ClientError, NoCredentialsError) as e:
            if settings.S3_ENDPOINT_URL and "supabase" in settings.S3_ENDPOINT_URL:
                clean_file_key = file_key.lstrip("/")
                encoded_key = urllib.parse.quote(clean_file_key, safe="/")
                return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{encoded_key}"

            raise Exception(f"Error generating presigned download URL: {str(e)}")

    def generate_signed_url(self, file_key: str, expiration: int = 3600) -> str:
        return self.generate_presigned_download_url(file_key, expiration)

    def generate_public_url(self, file_key: str) -> str:
        clean_file_key = file_key.lstrip("/")
        if settings.S3_ENDPOINT_URL:
            return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{clean_file_key}"
        else:
            return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{clean_file_key}"

    def delete_file(self, file_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)  # type: ignore
            return True

        except ClientError as e:
            print(f"Error deleting file from S3: {str(e)}")
            return False

    def download_file_content(self, file_key: str) -> bytes:
        """
        Downloads the content of a file from S3.

        Args:
            file_key (str): The key of the file in the S3 bucket.

        Returns:
            bytes: The raw content of the file.

        Raises:
            Exception: If the file cannot be downloaded.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)  # type: ignore
            return response["Body"].read()  # type: ignore
        except ClientError as e:
            print(f"Error downloading file {file_key} from S3: {str(e)}")
            raise Exception(f"Error downloading file from S3: {str(e)}")

    def get_file_info(self, file_key: str) -> Optional[Dict]:  # type: ignore
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)  # type: ignore

            return {
                "size": response.get("ContentLength"),  # type: ignore
                "content_type": response.get("ContentType"),  # type: ignore
                "last_modified": response.get("LastModified"),  # type: ignore
                "etag": response.get("ETag", "").strip('"'),  # type: ignore
            }  # type: ignore

        except ClientError:
            return None

    def verify_file_exists(self, file_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)  # type: ignore
            return True
        except ClientError:
            return False


s3_manager = S3Manager()
