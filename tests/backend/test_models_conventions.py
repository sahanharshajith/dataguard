"""Rules that must hold for every table, now and for models added later."""

import app.models
from app.db.base import Base


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