from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False)
    sales_rep_id: Mapped[int] = mapped_column(
        ForeignKey("sales_reps.id", ondelete="RESTRICT"), nullable=False
    )
    order_date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "fulfilled", "cancelled", name="order_status_enum"),
        nullable=False,
        default="fulfilled",
    )
    payment_status: Mapped[str] = mapped_column(
        Enum("paid", "pending", "overdue", name="payment_status_enum"), nullable=False
    )
    payment_due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    payment_received_date: Mapped[dt.date | None] = mapped_column(Date)
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    college: Mapped["College"] = relationship(back_populates="orders")
    sales_rep: Mapped["SalesRep"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
