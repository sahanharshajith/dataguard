"""Helpers for building CHECK constraints."""

from enum import StrEnum

from sqlalchemy import CheckConstraint


def in_enum(column: str, enum_cls: type[StrEnum], name: str) -> CheckConstraint:
    """
    CHECK constraint restricting `column` to the values of `enum_cls` (decision DB3).

    The values come from our own enum classes, never from user input
    """
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=name)