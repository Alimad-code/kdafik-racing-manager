from decimal import Decimal

from app.core.errors import DomainError, ErrorCode
from app.domain.enums import BudgetCategory
from app.models import BudgetTransaction, Season
from app.repositories.season import make_budget_transaction


def free_budget(season: Season) -> Decimal:
    return max(
        season.available_budget_millions
        - season.repair_reserve_millions
        - season.setup_reserve_millions,
        Decimal("0.00"),
    )


def available_for_category(season: Season, category: BudgetCategory) -> Decimal:
    free = free_budget(season)
    if category == BudgetCategory.SETUP:
        return min(season.available_budget_millions, season.setup_reserve_millions + free)
    if category == BudgetCategory.REPAIR:
        return min(season.available_budget_millions, season.repair_reserve_millions + free)
    return free


def require_sufficient_funds(
    season: Season,
    required_amount: Decimal,
    message: str,
    *,
    category: BudgetCategory,
) -> None:
    available_amount = available_for_category(season, category)
    if available_amount >= required_amount:
        return
    raise DomainError(
        ErrorCode.INSUFFICIENT_FUNDS,
        message,
        details={
            "availableMillions": float(available_amount),
            "requiredMillions": float(required_amount),
        },
    )


def spend_budget(
    season: Season,
    *,
    category: BudgetCategory,
    label: str,
    amount: Decimal,
    reference_type: str,
    reference_id: str,
    insufficient_funds_message: str = "Недостаточно средств для действия.",
) -> BudgetTransaction | None:
    if amount < 0:
        raise ValueError("Budget expense cannot be negative.")
    if amount == 0:
        return None
    require_sufficient_funds(
        season,
        amount,
        insufficient_funds_message,
        category=category,
    )
    reserve_applied = Decimal("0.00")
    if category == BudgetCategory.SETUP:
        reserve_applied = min(amount, season.setup_reserve_millions)
    elif category == BudgetCategory.REPAIR:
        reserve_applied = min(amount, season.repair_reserve_millions)
    free_applied = amount - reserve_applied
    transaction = make_budget_transaction(
        season=season,
        category=category,
        label=label,
        amount=amount,
        reserve_applied=reserve_applied,
        free_applied=free_applied,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    season.budget_transactions.append(transaction)
    if getattr(season, "_available_budget_override", None) is not None:
        season.available_budget_millions = season.available_budget_millions - amount
    return transaction
