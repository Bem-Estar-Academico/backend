import uuid
from datetime import datetime
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import settings


class S3Manager:

    def __init__(self):
        client_args = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
        }

        if settings.S3_ENDPOINT_URL:
            client_args["endpoint_url"] = settings.S3_ENDPOINT_URL

        self.s3_client = boto3.client("s3", **client_args)
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_unique_filename(self, original_filename: str) -> str:
        file_parts = original_filename.rsplit(".", 1)
        name = file_parts[0]
        extension = file_parts[1] if len(file_parts) > 1 else ""

        now = datetime.now()
        year_month = now.strftime("%Y/%m")

        unique_id = str(uuid.uuid4())[:8]

        clean_name = "".join(c for c in name if c.isalnum() or c in "._- ")[:50]

        if extension:
            filename = f"{unique_id}_{clean_name}.{extension}"
        else:
            filename = f"{unique_id}_{clean_name}"

        return f"documents/{year_month}/{filename}"

    def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        try:
            unique_filename = self.generate_unique_filename(filename)

            self.s3_client.put_object(
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
        self, file_key: str, expiration: int = 3600
    ) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expiration,
            )
            return url

        except (ClientError, NoCredentialsError) as e:
            raise Exception(f"Error generating presigned download URL: {str(e)}")

    def delete_file(self, file_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True

        except ClientError as e:
            print(f"Error deleting file from S3: {str(e)}")
            return False

    def get_file_info(self, file_key: str) -> Optional[Dict]:
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)

            return {
                "size": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag", "").strip('"'),
            }

        except ClientError:
            return None

    def verify_file_exists(self, file_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError:
            return False


s3_manager = S3Manager()
