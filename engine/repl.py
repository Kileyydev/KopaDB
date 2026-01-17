from engine.database import Database
from engine.parser import parse, ParseError

db = Database()


def pretty_print(rows):
    if not rows:
        print("No results.")
        return

    columns = list(rows[0].keys())
    widths = {
        c: max(len(str(r[c])) for r in rows + [{c: c}])
        for c in columns
    }

    header = " | ".join(c.ljust(widths[c]) for c in columns)
    sep = "-+-".join("-" * widths[c] for c in columns)

    print(header)
    print(sep)

    for row in rows:
        print(" | ".join(str(row[c]).ljust(widths[c]) for c in columns))


print("🚀 Welcome to KopaDB (type 'exit' to quit)")


while True:
    try:
        cmd = input("kopadb> ").strip()

        if not cmd:
            continue

        if cmd.lower() == "exit":
            print("Goodbye!")
            break

        # remove trailing semicolon safely
        if cmd.endswith(";"):
            cmd = cmd[:-1]

        parsed = parse(cmd)
        if not parsed:
            continue

        cmd_type = parsed["type"]

        # ================= CREATE =================
        if cmd_type == "CREATE":
            table_name = parsed["table"]
            columns = parsed["columns"]

            db.create_table(
                table_name,
                columns,
                primary_key=columns[0][0]
            )

            print(f"✅ Table '{table_name}' created.")

        # ================= INSERT =================
        elif cmd_type == "INSERT":
            table_name = parsed["table"]
            table = db.tables[table_name]
            values = parsed["values"]

            if len(values) != len(table.columns):
                raise ValueError("Column count does not match values count")

            row = dict(zip(table.columns, values))
            db.insert(table_name, row)

            print(f"✅ Row inserted into '{table_name}'.")

        # ================= SELECT =================
        elif cmd_type == "SELECT":
            table_name = parsed["table"]
            filters = parsed.get("where")

            rows = db.select_all(table_name, filters)
            pretty_print(rows)

        # ================= UPDATE =================
        elif cmd_type == "UPDATE":
            table_name = parsed["table"]
            set_values = parsed["set"]
            where_filters = parsed.get("where")

            count = db.update(table_name, where_filters, set_values)
            print(f"✅ {count} row(s) updated in '{table_name}'.")

        # ================= DELETE =================
        elif cmd_type == "DELETE":
            table_name = parsed["table"]
            where_filters = parsed.get("where")

            count = db.delete(table_name, where_filters)
            print(f"✅ {count} row(s) deleted from '{table_name}'.")

        # ================= INDEX =================
        elif cmd_type == "INDEX":
            table_name = parsed["table"]
            column = parsed["column"]

            db.create_index(table_name, column)
            print(f"✅ Index created on '{column}' in '{table_name}'.")

        # ================= JOIN =================
        elif cmd_type == "JOIN":
            left = parsed["left_table"]
            right = parsed["right_table"]
            left_key = parsed["left_key"]
            right_key = parsed["right_key"]

            rows = db.inner_join(left, right, left_key, right_key)
            pretty_print(rows)

        else:
            print("⚠️ Unsupported command.")

    except ParseError as pe:
        print("❌ Syntax Error:", pe)

    except Exception as e:
        print("❌ Error:", e)
