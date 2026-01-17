import datetime
from engine.index import Index


class Table:
    SUPPORTED_TYPES = {"INT", "FLOAT", "TEXT", "TIMESTAMP"}

    def __init__(self, name, columns, primary_key=None, unique_keys=None):
        self.name = name
        self.schema = {}
        self.columns = []

        for col in columns:
            if isinstance(col, tuple):
                col_name, dtype = col
                dtype = dtype.upper()
                if dtype not in self.SUPPORTED_TYPES:
                    raise ValueError(f"Unsupported type: {dtype}")
                self.schema[col_name] = dtype
                self.columns.append(col_name)
            else:
                self.schema[col] = "TEXT"
                self.columns.append(col)

        self.primary_key = primary_key
        self.unique_keys = unique_keys or []
        self.rows = []
        self.indexes = {}  # column -> Index

    # ---------------- INTERNAL ----------------
    def _cast(self, column, value):
        if value is None:
            return None

        dtype = self.schema.get(column)
        if not dtype:
            return value

        try:
            if dtype == "INT":
                return int(value)
            if dtype == "FLOAT":
                return float(value)
            if dtype == "TEXT":
                return str(value)
            if dtype == "TIMESTAMP":
                if isinstance(value, datetime.datetime):
                    return value.isoformat()
                return str(value)
        except (ValueError, TypeError):
            raise ValueError(
                f"Cannot cast {value!r} to {dtype} for column '{column}'"
            )

        return value

    # ---------------- INSERT ----------------
    def insert(self, row):
        new_row = {}

        for col in self.columns:
            if col in row:
                new_row[col] = self._cast(col, row[col])
            elif self.schema[col] == "TIMESTAMP":
                new_row[col] = datetime.datetime.now().isoformat()
            else:
                new_row[col] = None

        # Primary key constraint
        if self.primary_key:
            pk_val = new_row[self.primary_key]
            for r in self.rows:
                if r[self.primary_key] == pk_val:
                    raise ValueError(
                        f"Primary key violation on {self.primary_key} = {pk_val}"
                    )

        # Unique constraints
        for uk in self.unique_keys:
            uk_val = new_row[uk]
            for r in self.rows:
                if r[uk] == uk_val:
                    raise ValueError(
                        f"Unique constraint violation on {uk} = {uk_val}"
                    )

        self.rows.append(new_row)

        # Update indexes
        for col, idx in self.indexes.items():
            idx.add(new_row[col], new_row)

        return new_row

    # ---------------- SELECT ----------------
    def select_all(self, filters=None):
        if not filters:
            return list(self.rows)

        result = self.rows

        for col, want in filters:
            want = self._cast(col, want)

            if col in self.indexes:
                result = self.indexes[col].lookup(want)
            else:
                result = [r for r in result if r.get(col) == want]

        return list(result)

    # ---------------- UPDATE ----------------
    def update(self, filters, updates):
        rows = self.select_all(filters)
        count = len(rows)

        for row in rows:
            # Remove from indexes
            for col, idx in self.indexes.items():
                idx.remove(row[col], row)

            for col, val in updates.items():
                if col in self.schema:
                    row[col] = self._cast(col, val)

            if "updated_at" in self.schema:
                row["updated_at"] = datetime.datetime.now().isoformat()

            # Re-add to indexes
            for col, idx in self.indexes.items():
                idx.add(row[col], row)

        return count

    # ---------------- DELETE ----------------
    def delete(self, filters):
        to_delete = self.select_all(filters)
        count = len(to_delete)

        for row in to_delete:
            for col, idx in self.indexes.items():
                idx.remove(row[col], row)
            self.rows.remove(row)

        return count

    # ---------------- INDEX ----------------
    def create_index(self, column):
        """
        Create and attach a new index on the given column.
        Automatically rebuilds it using current table rows.
        """
        if column not in self.schema:
            raise ValueError(
                f"Column '{column}' does not exist in table '{self.name}'"
            )

        if column in self.indexes:
            print(f"→ Index on '{column}' already exists (skipping)")
            return

        idx = Index(column)
        idx.rebuild(self.rows)
        self.indexes[column] = idx

        print(
            f"→ Index created on column '{column}' "
            f"({len(self.rows)} rows indexed)"
        )
