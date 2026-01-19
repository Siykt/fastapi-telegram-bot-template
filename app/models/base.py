"""SQLAlchemy Base model with snowflake ID support."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.utils.snowflake import generate_id


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class BaseModel(Base):
    """Base model with snowflake ID, timestamps and audit fields."""
    __abstract__ = True

    # sort_order 负数确保基类字段在子类字段之前
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_id, sort_order=-10, comment="主键(雪花算法)")
    create_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, sort_order=90, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, sort_order=91, comment="更新人ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), sort_order=92, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), sort_order=93, comment="更新时间")
    remark: Mapped[str | None] = mapped_column(String(512), nullable=True, sort_order=99, comment="备注")
