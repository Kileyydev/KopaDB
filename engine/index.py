class Index:
    def __init__(self, column):
        self.column = column
        self.map = {}

    def add(self, value, row):
        if value not in self.map:
            self.map[value] = []
        self.map[value].append(row)

    def lookup(self, value):
        return self.map.get(value, [])
