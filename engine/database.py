import json
import os
from .table import Table
from .index import Index

class Database:
    def __init__(self, data_file="kopadb_data.json"):
        self.tables = {}
        self.data_file = data_file
        self._load_data()

    # =========================
    # Persistence
    # =========================
    def _load_data(self):
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)

            for table_name, t in data.items():
                table = Table(
                    name=table_name,
                    columns=list(t["schema"].items()),  # schema → [(col, type)]
                    primary_key=t.get("primary_key"),
                    unique_keys=t.get("unique_keys", [])
                )
                table.rows = t.get("rows", [])

                # rebuild indexes
                for col in t.get("indexes", []):
                    idx = Index(col)
                    table.create_index(col, idx)

                self.tables[table_name] = table

            print(f"[Database] Loaded {len(self.tables)} tables")

        except Exception as e:
            print("[Database] Load failed:", e)
            self.tables = {}

    def _save_data(self):
        data = {}
        for name, table in self.tables.items():
            data[name] = {
                "schema": table.schema,
                "rows": table.rows,
                "primary_key": table.primary_key,
                "unique_keys": table.unique_keys,
                "indexes": list(table.indexes.keys())
            }

        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)

    # =========================
    # Schema
    # =========================
    def create_table(self, name, columns, primary_key=None, unique_keys=None):
        if name in self.tables:
            raise ValueError("Table already exists")

        # normalize columns
        if isinstance(columns, dict):
            normalized = list(columns.items())
        elif isinstance(columns, list):
            normalized = columns
        else:
            raise ValueError("Invalid columns format")

        self.tables[name] = Table(
            name=name,
            columns=normalized,
            primary_key=primary_key,
            unique_keys=unique_keys or []
        )

        self._save_data()

    def show_tables(self):
        return list(self.tables.keys())

    def describe_table(self, table_name):
        table = self._get_table(table_name)
        return {
            "schema": table.schema,
            "primary_key": table.primary_key,
            "unique_keys": table.unique_keys,
            "indexes": list(table.indexes.keys())
        }

    # =========================
    # CRUD
    # =========================
    def insert(self, table_name, row):
        table = self._get_table(table_name)
        table.insert(row)
        self._save_data()

    def select_all(self, table_name, filters=None):
        table = self._get_table(table_name)
        return table.select_all(filters)

    def update(self, table_name, where, updates):
        table = self._get_table(table_name)
        table.update(where, updates)
        self._save_data()
        return True

    def delete(self, table_name, where):
        table = self._get_table(table_name)
        table.delete(where)
        self._save_data()
        return True

    # =========================
    # Indexing
    # =========================
    def create_index(self, table_name, column):
        table = self._get_table(table_name)
        table.create_index(column, Index(column))
        self._save_data()
        print(f"[DB] Index created on {table_name}.{column}")

    # =========================
    # Joins
    # =========================
    def inner_join(self, left_table, right_table, left_key, right_key):
        left = self._get_table(left_table)
        right = self._get_table(right_table)
        result = []
        for l in left.rows:
            for r in right.rows:
                if l[left_key] == r[right_key]:
                    result.append({**l, **r})
        return result

    # =========================
    # Helpers
    # =========================
    def _get_table(self, table_name):
        if table_name not in self.tables:
            raise ValueError(f"Table '{table_name}' not found")
        return self.tables[table_name]
