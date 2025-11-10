"""
Service for generating Excel reports from IVS data.
"""

import csv
import io
from datetime import datetime, timezone
from typing import BinaryIO, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.core.logging_config import get_logger
from app.schemas.ivs import IVSData

logger = get_logger(__name__)


class ExcelReportService:
    """Service for generating Excel reports."""
    
    @staticmethod
    def generate_ivs_report_csv(ivs_data: List[IVSData], anonymous: bool = False) -> BinaryIO:
        """
        Gera um relatório CSV com dados IVS.
        """
        
        string_buffer = io.StringIO()
        
        writer = csv.writer(string_buffer, delimiter=';') 

        headers = [
            "Matrícula", "CPF", "Edital", 
            "Ano do Edital", "IVS Calculado", "Data de Expiração", "Status"
        ]
        writer.writerow(headers)

        current_date = datetime.now(timezone.utc)

        for ivs_item in ivs_data:
            expiration_date = ivs_item.expiration_date
            if expiration_date is not None and expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=timezone.utc)
            status = "Ativo" if expiration_date and expiration_date > current_date else "Expirado"
            
            if anonymous:
                cpf = getattr(ivs_item.student, "cpf", None) or "N/A"
                cpf_digits = "".join(filter(str.isdigit, cpf))
                    
                cpf = f"{cpf_digits[0:3]}.***.***-{cpf_digits[len(cpf_digits) - 2: len(cpf_digits)]}"
                
                registration_number = ivs_item.student.registration_number
                registration_number = f"{registration_number[0:2]}*****{registration_number[len(registration_number) - 2:len(registration_number)]}"
                
                row_data = [
                    registration_number,
                    cpf,
                    ivs_item.notice.title or "N/A",
                    (
                        f"{ivs_item.ivs_score:.2f}"
                        if ivs_item.ivs_score is not None
                        else "N/A"
                    ),
                    (
                        ivs_item.expiration_date.strftime("%d/%m/%Y")
                        if ivs_item.expiration_date
                        else "N/A"
                    ),
                    status,
                ]
                
                writer.writerow(row_data)
            else:
                row_data = [
                ivs_item.student.full_name or "N/A",
                ivs_item.student.email or "N/A",
                ivs_item.student.registration_number or "N/A",
                getattr(ivs_item.student, "cpf", None) or "N/A",
                ivs_item.notice.title or "N/A",
                (
                    f"{ivs_item.ivs_score:.2f}"
                    if ivs_item.ivs_score is not None
                    else "N/A"
                ),
                (
                    ivs_item.expiration_date.strftime("%d/%m/%Y")
                    if ivs_item.expiration_date
                    else "N/A"
                ),
                status,
                ]
                
                writer.writerow(row_data)
                

        bytes_buffer = io.BytesIO(string_buffer.getvalue().encode('utf-8-sig'))
        bytes_buffer.seek(0)
        
        logger.info(f"CSV report generated with {len(ivs_data)} IVS records")
        return bytes_buffer

    @staticmethod
    def generate_csv_filename(anonymous: bool = True) -> str:
        """
        Gera o nome do arquivo para o relatório IVS em CSV.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if anonymous:
            return f"relatorio_ivs_anonimo_{timestamp}.csv"
        return f"relatorio_ivs_completo_{timestamp}.csv"


excel_report_service = ExcelReportService()
