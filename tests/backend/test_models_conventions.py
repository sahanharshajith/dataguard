"""Rules that must hold for every table, now and for models added later."""

import app.models
from app.db.base import Base
from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint


def test_foreign_keys_have_the_same_type_as_the_columns_they_reference():
    # Guards against e.g. an INTEGER column pointing at a BIGINT primary key.
    for table in Base.metadata.tables.values():
        for column in table.columns:
            for foreign_key in column.foreign_keys:
                referenced = foreign_key.column
                assert type(column.type) is type(referenced.type), (
                    f"{table.name}.{column.name} is {column.type!r} "
                    f"but references {referenced.table.name}.{referenced.name} ({referenced.type!r})"
                )


def test_every_table_has_a_primary_key():
    for table in Base.metadata.tables.values():
        assert table.primary_key.columns, f"{table.name} has no primary key"

def leading_columns(table) -> set[str]:
    """Columns that start some index, unique constraint, or the primary key."""
    leading = {list(index.columns)[0].name for index in table.indexes}
    for constraint in table.constraints:
        if isinstance(constraint, (UniqueConstraint, PrimaryKeyConstraint)):
            leading.add(list(constraint.columns)[0].name)
    return leading


def test_every_foreign_key_column_starts_an_index():
    # PostgreSQL does not index foreign keys itself; without one, joins and cascades get slow.
    for table in Base.metadata.tables.values():
        covered = leading_columns(table)
        for column in table.columns:
            if column.foreign_keys:
                assert column.name in covered, f"{table.name}.{column.name} has no index"