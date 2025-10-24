from typing import Optional

from app.core.storage_interface import StorageInterface


class StorageFactory:
    _instance: Optional[StorageInterface] = None

    @classmethod
    def get_storage_manager(cls) -> StorageInterface:
        if cls._instance is None:
            cls._instance = cls._create_storage_manager()
        return cls._instance

    @classmethod
    def _create_storage_manager(cls) -> StorageInterface:
        from app.core.s3_manager import s3_manager

        return s3_manager

    @classmethod
    def reset(cls):
        cls._instance = None


def get_storage_manager() -> StorageInterface:
    return StorageFactory.get_storage_manager()
