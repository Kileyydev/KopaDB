import json
import os
from .table import Table
from .index import Index

class Database:
    def __init__(self):
        self.tables = {}
        self.data_file = "kopadb_data.json"  # File where data is saved
        self._load_data()  # Load from disk on startup

    def _load_data(self):
        """Load all tables from JSON file if it exists"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                for table_name, table_data in data.items():
                    # Rebuild Table object
                    table = Table(
                        name=table_name,
                        columns=table_data["columns"],
                        primary_key=table_data.get("primary_key"),
                        unique_keys=table_data.get("unique_keys")
                    )
                    table.rows = table_data["rows"]  # Restore rows
                    table.indexes = table_data.get("indexes", {})  # Restore indexes if any
                    self.tables[table_name] = table
                print(f"[Database] Loaded {len(self.tables)} tables from disk")
            except Exception as e:
                print(f"[Database] Error loading data: {e}")
                self.tables = {}  # Start fresh if corrupted

    def _save_data(self):
        """Save all tables to JSON file"""
        try:
            data = {}
            for name, table in self.tables.items():
                data[name] = {
                    "columns": table.columns,
                    "rows": table.rows,
                    "primary_key": table.primary_key,
                    "unique_keys": table.unique_keys,
                    "indexes": table.indexes  # Save indexes too if implemented
                }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[Database] Saved {len(self.tables)} tables to disk")
        except Exception as e:
            print(f"[Database] Error saving data: {e}")

    def create_table(self, name, columns, primary_key=None, unique_keys=None):
        if name in self.tables:
            raise ValueError("Table already exists")
        self.tables[name] = Table(name, columns, primary_key, unique_keys)
        self._save_data()  # Persist after creation

    def insert(self, table_name, row):
        table = self.tables.get(table_name)
        if not table:
            raise ValueError("Table not found")
        table.insert(row)

        # Auto-update merchant balance if transaction
        if table_name == "transactions":
            self._update_merchant_balance(row)

        self._save_data()  # ← CRITICAL: Save after every insert!

    def _update_merchant_balance(self, transaction):
        merchant_id = transaction["merchant_id"]
        merchant_table = self.tables.get("merchants")
        if not merchant_table:
            return

        for m in merchant_table.rows:
            if m["id"] == merchant_id:
                if transaction["status"] == "complete":
                    current_balance = float(m.get("balance", 0))
                    m["balance"] = current_balance + float(transaction["amount"])
                self._save_data()  # Save balance update too

    def select_all(self, table_name, filters=None):
        table = self.tables.get(table_name)
        if not table:
            raise ValueError("Table not found")
        return table.select_all(filters)

    def create_index(self, table_name, column):
        table = self.tables.get(table_name)
        if not table:
            raise ValueError("Table not found")
        index = Index(column)
        table.create_index(column, index)
        self._save_data()  # Persist index creation

    def inner_join(self, left_table, right_table, left_key, right_key):
        left = self.tables[left_table]
        right = self.tables[right_table]
        result = []

        for l in left.rows:
            for r in right.rows:
                if l.get(left_key) == r.get(right_key):
                    result.append({**l, **r})
        return result

    # Optional: Add these helper methods if you want full CRUD persistence
    def update(self, table_name, row_id, updates):
        table = self.tables.get(table_name)
        if not table:
            raise ValueError("Table not found")
        table.update(row_id, updates)
        self._save_data()

    def delete(self, table_name, row_id):
        table = self.tables.get(table_name)
        if not table:
            raise ValueError("Table not found")
        table.delete(row_id)
        self._save_data()