from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, func, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Email обязателен и является User ID в понимании Dexpay [cite: 602]
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    # Внутренний ID Dexpay
    dexpay_internal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- KYC - "status": "NONE || PROCESS || REJECTED || APPROVED" - APPROVED = True
    kyc_status: Mapped[str] = mapped_column(String(20), default="NONE")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reg_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    orders = relationship("Order", back_populates="user")


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.user_id'))

    order_type: Mapped[str] = mapped_column(String(10), nullable=False, default="buy")

    # --- Финансы ---
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Точность до 6 знаков [cite: 273]
    amount_usdt: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    network_fee_rub: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total_payment_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # --- Реквизиты ---
    wallet_address: Mapped[str] = mapped_column(String(128), nullable=False)
    network: Mapped[str] = mapped_column(String(20), default="BEP20")

    # --- Данные Dexpay ---
    dexpay_order_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    # Ссылка на оплату.
    # ВАЖНО: Показывать ее пользователю можно ТОЛЬКО если user.is_verified = True [cite: 611]
    payment_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    user = relationship("User", back_populates="orders")