from enum import StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum


def enum_type[EnumType: StrEnum](
    enum_class: type[EnumType],
    name: str,
    length: int = 64,
) -> SQLAlchemyEnum:
    return SQLAlchemyEnum(
        enum_class,
        values_callable=lambda values: [item.value for item in values],
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
    )
