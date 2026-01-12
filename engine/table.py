import datetime

class Table:
    def __init__(self, name, columns, primary_key=None, unique_keys=None):
        """
        Initialize a Table.

        :param name: Table name
        :param columns: List of column names
        :param primary_key: Optional primary key column
        :param unique_keys: Optional list of columns with unique constraints
        """
        self.name = name
        self.columns = columns
        self.primary_key = primary_key
        self.unique_keys = unique_keys or []
        self.rows = []
        self.indexes = {}  # {column_name: Index instance}

    def insert(self, row):
        """
        Insert a row into the table. Auto-fills timestamps if columns exist.
        Enforces primary key and unique constraints.
        """
        full_row = {}
        for col in self.columns:
            if col in row:
                full_row[col] = row[col]
            else:
                # Auto-fill timestamps
                if col in ("created_at", "updated_at", "timestamp"):
                    full_row[col] = datetime.datetime.now().isoformat()
                else:
                    full_row[col] = None  # Fill missing columns with None

        # Primary key check
        if self.primary_key:
            for r in self.rows:
                if r[self.primary_key] == full_row[self.primary_key]:
                    raise ValueError(f"Primary key violation: {self.primary_key}={full_row[self.primary_key]}")

        # Unique key checks
        for key in self.unique_keys:
            for r in self.rows:
                if r[key] == full_row[key]:
                    raise ValueError(f"Unique constraint violation on column: {key}")

        # Add the row
        self.rows.append(full_row)

        # Update indexes
        for col, index in self.indexes.items():
            index.add(full_row[col], full_row)

    def create_index(self, column, index):
        """
        Attach an Index object to a column for fast lookups.
        """
        self.indexes[column] = index
        for row in self.rows:
            index.add(row[column], row)

    def select_all(self, filters=None):
        """
        Select all rows, optionally applying filters as a dict.
        """
        results = self.rows
        if filters:
            for key, val in filters.items():
                results = [r for r in results if r.get(key) == val]
        return results

    def update(self, filters, updates):
        """
        Update rows that match filters.
        """
        rows = self.select_all(filters)
        for row in rows:
            for key, val in updates.items():
                if key in self.columns:
                    row[key] = val
            if "updated_at" in self.columns:
                row["updated_at"] = datetime.datetime.now().isoformat()

    def delete(self, filters):
        """
        Delete rows that match filters.
        """
        self.rows = [r for r in self.rows if not all(r.get(k) == v for k, v in filters.items())]
