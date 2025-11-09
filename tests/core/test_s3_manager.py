from unittest.mock import ANY, MagicMock, patch

import pytest

from app.core.s3_manager import S3Manager


@pytest.fixture
def mock_boto3_client():
    with patch("boto3.client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_settings():
    with patch("app.core.s3_manager.settings") as mock_settings:
        mock_settings.AWS_ACCESS_KEY_ID = "test_access_key"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test_secret_key"
        mock_settings.AWS_REGION = "us-east-1"
        mock_settings.S3_BUCKET_NAME = "test_bucket"
        mock_settings.S3_ENDPOINT_URL = None
        yield mock_settings


def test_s3_manager_init(mock_boto3_client, mock_settings):
    S3Manager()
    mock_boto3_client.assert_called_once_with(
        "s3",
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        region_name="us-east-1",
        config=ANY,
    )


def test_generate_unique_filename():
    s3_manager = S3Manager()
    filename = "test_file.txt"
    unique_filename = s3_manager.generate_unique_filename(filename)
    assert unique_filename.startswith("documents/")
    assert unique_filename.endswith("_test_file.txt")


def test_upload_file(mock_boto3_client, mock_settings):
    s3_manager = S3Manager()
    s3_manager.s3_client = MagicMock()
    file_content = b"test_content"
    filename = "test_file.txt"
    content_type = "text/plain"
    unique_filename = s3_manager.upload_file(file_content, filename, content_type)
    s3_manager.s3_client.put_object.assert_called_once()
    assert unique_filename.startswith("documents/")


def test_generate_presigned_download_url(mock_boto3_client, mock_settings):
    s3_manager = S3Manager()
    s3_manager.s3_client = MagicMock()
    file_key = "test_key"
    url = s3_manager.generate_presigned_download_url(file_key)
    s3_manager.s3_client.generate_presigned_url.assert_called_once()
    assert url is not None


def test_delete_file(mock_boto3_client, mock_settings):
    s3_manager = S3Manager()
    s3_manager.s3_client = MagicMock()
    file_key = "test_key"
    result = s3_manager.delete_file(file_key)
    s3_manager.s3_client.delete_object.assert_called_once_with(
        Bucket="test_bucket", Key=file_key
    )
    assert result is True


def test_download_file_content(mock_boto3_client, mock_settings):
    s3_manager = S3Manager()
    s3_manager.s3_client = MagicMock()
    s3_manager.s3_client.get_object.return_value = {"Body": MagicMock()}
    file_key = "test_key"
    content = s3_manager.download_file_content(file_key)
    s3_manager.s3_client.get_object.assert_called_once_with(
        Bucket="test_bucket", Key=file_key
    )
    assert content is not None


def test_get_file_info(mock_boto3_client, mock_settings):
    s3_manager = S3Manager()
    s3_manager.s3_client = MagicMock()
    file_key = "test_key"
    info = s3_manager.get_file_info(file_key)
    s3_manager.s3_client.head_object.assert_called_once_with(
        Bucket="test_bucket", Key=file_key
    )
    assert info is not None


def test_verify_file_exists(mock_boto3_client, mock_settings):
    s3_manager = S3Manager()
    s3_manager.s3_client = MagicMock()
    file_key = "test_key"
    exists = s3_manager.verify_file_exists(file_key)
    s3_manager.s3_client.head_object.assert_called_once_with(
        Bucket="test_bucket", Key=file_key
    )
    assert exists is True
