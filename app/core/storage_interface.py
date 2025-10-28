from abc import ABC, abstractmethod
from typing import Dict, Optional


class StorageInterface(ABC):
    @abstractmethod
    def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        """Upload de arquivo e retorna a chave/path do arquivo"""
        pass

    @abstractmethod
    def delete_file(self, file_key: str) -> bool:
        """Deleta arquivo e retorna True se bem-sucedido"""
        pass

    @abstractmethod
    def generate_signed_url(self, file_key: str, expiration: int = 3600) -> str:
        """Gera URL assinada para download do arquivo"""
        pass

    @abstractmethod
    def verify_file_exists(self, file_key: str) -> bool:
        """Verifica se o arquivo existe no storage"""
        pass

    @abstractmethod
    def get_file_info(self, file_key: str) -> Optional[Dict]:
        """Retorna informações do arquivo"""
        pass
