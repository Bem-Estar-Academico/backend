"""
Service for generating Excel reports from IVS data.
"""

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
    def generate_ivs_report(ivs_data: List[IVSData]) -> BinaryIO:
        """
        Generate Excel report with IVS data.

        Args:
            ivs_data: List of IVS data objects

        Returns:
            BinaryIO: Excel file as bytes
        """

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Relatório IVS"

        headers = [
            "Nome do Estudante",
            "Email",
            "Matrícula",
            "CPF",
            "Edital",
            "Ano do Edital",
            "IVS Calculado",
            "Data de Expiração",
            "Status",
        ]

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="366092", end_color="366092", fill_type="solid"
        )
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border

        for row_idx, ivs_item in enumerate(ivs_data, 2):
            current_date = datetime.now(timezone.utc)
            status = "Ativo" if ivs_item.expiration_date > current_date else "Expirado"

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

            for col_idx, value in enumerate(row_data, 1):
                cell = worksheet.cell(row=row_idx, column=col_idx, value=value)
                cell.border = border
                cell.alignment = Alignment(vertical="center")

                if status == "Expirado":
                    cell.fill = PatternFill(
                        start_color="FFE6E6", end_color="FFE6E6", fill_type="solid"
                    )

        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass

            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

        summary_row = len(ivs_data) + 3
        worksheet.cell(row=summary_row, column=1, value="Resumo:")
        worksheet.cell(row=summary_row, column=1).font = Font(bold=True)

        total_students = len(ivs_data)
        active_count = sum(
            1 for item in ivs_data if item.expiration_date > datetime.now(timezone.utc)
        )
        expired_count = total_students - active_count

        worksheet.cell(
            row=summary_row + 1,
            column=1,
            value=f"Total de estudantes: {total_students}",
        )
        worksheet.cell(
            row=summary_row + 2, column=1, value=f"IVS ativos: {active_count}"
        )
        worksheet.cell(
            row=summary_row + 3, column=1, value=f"IVS expirados: {expired_count}"
        )

        timestamp_row = summary_row + 5
        timestamp = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
        worksheet.cell(
            row=timestamp_row, column=1, value=f"Relatório gerado em: {timestamp}"
        )
        worksheet.cell(row=timestamp_row, column=1).font = Font(italic=True, size=10)

        excel_buffer = io.BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)

        logger.info(f"Excel report generated with {len(ivs_data)} IVS records")
        return excel_buffer

    @staticmethod
    def generate_filename() -> str:
        """
        Generate filename for IVS report.

        Returns:
            str: Filename with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"relatorio_ivs_{timestamp}.xlsx"


excel_report_service = ExcelReportService()
