from engine.database import Database
from engine.parser import parse

db = Database()

def pretty_print(rows):
    if not rows:
        print("No results.")
        return
    # get columns from first row
    columns = list(rows[0].keys())
    widths = [max(len(str(row[col])) for row in rows + [{col: col}]) for col in columns]

    # header
    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    sep = "-+-".join('-' * widths[i] for i in range(len(columns)))
    print(header)
    print(sep)

    # rows
    for row in rows:
        print(" | ".join(str(row[col]).ljust(widths[i]) for i, col in enumerate(columns)))

print("Welcome to KopaDB. Type 'exit' to quit.")

while True:
    try:
        command = input("kopadb> ").strip()
        if command.lower() == "exit":
            print("Goodbye!")
            break
        if not command:
            continue

        parsed = parse(command)
        if not parsed:
            continue

        action, tokens = parsed

        if action == "CREATE":
            table = tokens[2]
            columns = tokens[3].strip("()").split(",")
            db.create_table(table, columns, primary_key=columns[0])
            print(f"Table {table} created.")

        elif action == "INSERT":
            table = tokens[2]
            values = tokens[4].strip("()").split(",")
            row = dict(zip(db.tables[table].columns, values))
            db.insert(table, row)
            print("Row inserted.")

        elif action == "SELECT":
            table = tokens[3]
            rows = db.select_all(table)
            pretty_print(rows)

        elif action == "WHERE":
            table = tokens[1]
            column = tokens[2]
            value = tokens[3]
            rows = db.select_where(table, column, value)
            pretty_print(rows)

        elif action == "INDEX":
            table = tokens[2]
            column = tokens[3]
            db.create_index(table, column)
            print("Index created.")

        elif action == "JOIN":
            result = db.inner_join(tokens[1], tokens[2], tokens[3], tokens[4])
            pretty_print(result)

        else:
            print("Unknown command.")

    except Exception as e:
        print("Error:", e)
