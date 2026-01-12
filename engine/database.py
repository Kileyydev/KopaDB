from .table import Table
from .index import Index

class Database:
    def __init__(self):
        self.tables = {}

    def create_table(self, name, columns, primary_key=None, unique_keys=None):
        if name in self.tables:
            raise ValueError("Table already exists")
        self.tables[name] = Table(name, columns, primary_key, unique_keys)

    def insert(self, table_name, row):
        table = self.tables.get(table_name)
        if not table:
            raise ValueError("Table not found")
        table.insert(row)

        # Auto-update merchant balance if transaction
        if table_name == "transactions":
            self._update_merchant_balance(row)

    def _update_merchant_balance(self, transaction):
        merchant_id = transaction["merchant_id"]
        merchant_table = self.tables.get("merchants")
        for m in merchant_table.rows:
            if m["id"] == merchant_id:
                if transaction["status"] == "complete":
                    m["balance"] += float(transaction["amount"])

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

    def inner_join(self, left_table, right_table, left_key, right_key):
        left = self.tables[left_table]
        right = self.tables[right_table]
        result = []

        for l in left.rows:
            for r in right.rows:
                if l[left_key] == r[right_key]:
                    result.append({**l, **r})
        return result
