class Index:
    """
    Hash-based index for equality lookups.
    """
    def __init__(self, column):
        self.column = column
        self.map = {}  # value → [row, row, ...]

    def add(self, value, row):
        if value not in self.map:
            self.map[value] = []
        self.map[value].append(row)

    def remove(self, value, row):
        if value not in self.map:
            return
        try:
            self.map[value].remove(row)
            if not self.map[value]:
                del self.map[value]
        except ValueError:
            pass

    def lookup(self, value):
        return self.map.get(value, []).copy()

    def rebuild(self, rows):
        """Rebuild index from scratch"""
        self.map.clear()
        for row in rows:
            val = row.get(self.column)
            self.add(val, row)

    def clear(self):
        self.map.clear()

    def stats(self):
        return {
            "column": self.column,
            "distinct_values": len(self.map),
            "total_rows_indexed": sum(len(rows) for rows in self.map.values())
        }