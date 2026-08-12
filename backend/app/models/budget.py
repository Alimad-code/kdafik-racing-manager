from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import BudgetCategory
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.season import Season


class BudgetTransaction(Base):
    __tablename__ = "budget_transactions"
    __table_args__ = (
        CheckConstraint("amount_millions >= 0", name="ck_budget_transactions_amount_non_negative"),
        CheckConstraint(
            "reserve_applied_millions >= 0",
            name="ck_budget_transactions_reserve_applied_non_negative",
        ),
        CheckConstraint(
            "free_applied_millions >= 0",
            name="ck_budget_transactions_free_applied_non_negative",
        ),
        CheckConstraint(
            "reserve_applied_millions + free_applied_millions = amount_millions",
            name="ck_budget_transactions_applied_matches_amount",
        ),
        Index("ix_budget_transactions_season_id", "season_id"),
        Index("ix_budget_transactions_category", "category"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("seasons.id", ondelete="CASCADE"),
    )
    category: Mapped[BudgetCategory] = mapped_column(
        enum_type(BudgetCategory, "budget_category", 32)
    )
    label: Mapped[str] = mapped_column(String(180))
    amount_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    reserve_applied_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    free_applied_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    reference_type: Mapped[str | None] = mapped_column(String(80))
    reference_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    season: Mapped[Season] = relationship(back_populates="budget_transactions")

    @property
    def balance_before_millions(self) -> Decimal:
        balance = self.season.starting_budget_millions
        for transaction in self._ordered_season_transactions():
            if transaction.id == self.id:
                return balance
            balance -= transaction.amount_millions
        return balance

    @property
    def balance_after_millions(self) -> Decimal:
        return self.balance_before_millions - self.amount_millions

    def _ordered_season_transactions(self) -> list[BudgetTransaction]:
        return sorted(
            self.season.budget_transactions,
            key=lambda transaction: (
                _BUDGET_CATEGORY_ORDER.get(transaction.category.value, 99),
                transaction.created_at or datetime.min,
                str(transaction.id),
            ),
        )


_BUDGET_CATEGORY_ORDER = {
    "drivers": 0,
    "team": 1,
    "car-construction": 2,
    "setup": 3,
    "repair": 4,
}
