from engine.database import Database
from engine.parser import parse, ParseError


def pretty_print(rows):
    if not rows:
        print("No results.")
        return

    columns = list(rows[0].keys())
    widths = {
        c: max(len(str(r.get(c, ""))) for r in rows + [{c: c}])
        for c in columns
    }

    header = " | ".join(c.ljust(widths[c]) for c in columns)
    separator = "-+-".join("-" * widths[c] for c in columns)

    print(header)
    print(separator)

    for row in rows:
        print(" | ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns))


def print_help():
    print("""
Available commands:

CREATE TABLE table (col TYPE, col TYPE)
INSERT INTO table VALUES (v1, v2)

SELECT * FROM table
SELECT col1, col2 FROM table WHERE col=value AND col2=value

UPDATE table SET col=value WHERE col=value
DELETE FROM table WHERE col=value

INDEX ON table column

JOIN table1 table2 ON table1.col=table2.col

exit
""")


def main():
    db = Database()

    print("🚀 Welcome to KopaDB")
    print("Type 'help' for commands, 'exit' to quit\n")

    while True:
        try:
            cmd = input("kopadb> ").strip()

            if not cmd:
                continue

            if cmd.lower() == "exit":
                print("👋 Goodbye!")
                break

            if cmd.lower() == "help":
                print_help()
                continue

            # Remove trailing semicolon
            if cmd.endswith(";"):
                cmd = cmd[:-1]

            parsed = parse(cmd)
            if not parsed:
                continue

            cmd_type = parsed["type"]

            # ================= CREATE TABLE =================
            if cmd_type == "CREATE_TABLE":
                db.create_table(
                    parsed["table"],
                    parsed["columns"],
                    primary_key=parsed["columns"][0][0]
                )
                print(f"✅ Table '{parsed['table']}' created.")

            # ================= INSERT =================
            elif cmd_type == "INSERT":
                table = db.tables[parsed["table"]]
                if len(parsed["values"]) != len(table.columns):
                    raise ValueError("Column count does not match values count")

                row = dict(zip(table.columns, parsed["values"]))
                db.insert(parsed["table"], row)
                print(f"✅ Row inserted into '{parsed['table']}'.")

            # ================= SELECT =================
            elif cmd_type == "SELECT":
                rows = db.select_all(
                    parsed["table"],
                    parsed["where"]
                )

                # Column projection
                if parsed["columns"] != ["*"]:
                    rows = [
                        {c: r.get(c) for c in parsed["columns"]}
                        for r in rows
                    ]

                pretty_print(rows)

            # ================= UPDATE =================
            elif cmd_type == "UPDATE":
                count = db.update(
                    parsed["table"],
                    parsed["where"],
                    parsed["updates"]
                )
                print(f"✅ {count} row(s) updated.")

            # ================= DELETE =================
            elif cmd_type == "DELETE":
                count = db.delete(
                    parsed["table"],
                    parsed["where"]
                )
                print(f"✅ {count} row(s) deleted.")

            # ================= INDEX =================
            elif cmd_type == "CREATE_INDEX":
                db.create_index(
                    parsed["table"],
                    parsed["column"]
                )
                print(
                    f"✅ Index created on '{parsed['column']}' "
                    f"in '{parsed['table']}'."
                )

            # ================= JOIN =================
            elif cmd_type == "JOIN":
                rows = db.inner_join(
                    parsed["left_table"],
                    parsed["right_table"],
                    parsed["left_key"],
                    parsed["right_key"]
                )
                pretty_print(rows)

            else:
                print("⚠️ Unsupported command.")

        except ParseError as pe:
            print(f"❌ Syntax Error: {pe}")

        except KeyError as ke:
            print(f"❌ Unknown table or column: {ke}")

        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
