from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import now

from app.models.base import Base

class Period(Base):
    """
        Representation period.
        Atr:
        id (int): primary key.
        name (str): Descriptive name of period.
        init_date (datetime): Date of the period begin.
        end_date (datetime): Date of the period end.
        created_at (datetime): Create the instance.
        updated_at (datetime): Update the instance.
    """
    
    __tablename__ = "periods"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome descritivo do periodo"
    )
    init_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de início do período"
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de fim do período"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=now(),
        onupdate=now(),
        nullable=False,
    )
    