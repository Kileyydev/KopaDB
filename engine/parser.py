import shlex
import re


class ParseError(Exception):
    pass


KEYWORDS = {
    "CREATE", "TABLE", "INSERT", "INTO", "VALUES",
    "SELECT", "FROM", "WHERE",
    "UPDATE", "SET", "DELETE",
    "INDEX", "ON", "JOIN", "AND"
}


# ---------------- HELPERS ----------------
def parse_value(val):
    val = val.strip()
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1]
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val


def parse_conditions(tokens):
    """
    Parses WHERE a=1 AND b='x'
    Returns list of (column, value)
    """
    conditions = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "AND":
            i += 1
            continue
        if "=" not in tokens[i]:
            raise ParseError("Invalid WHERE condition")
        col, val = tokens[i].split("=", 1)
        conditions.append((col, parse_value(val)))
        i += 1
    return conditions


# ---------------- MAIN PARSER ----------------
def parse(command: str):
    if not command.strip():
        return None

    tokens = shlex.split(command)
    tokens = [t.upper() if t.upper() in KEYWORDS else t for t in tokens]

    cmd = tokens[0]

    if cmd == "CREATE":
        return parse_create(tokens)
    if cmd == "INSERT":
        return parse_insert(tokens)
    if cmd == "SELECT":
        return parse_select(tokens)
    if cmd == "UPDATE":
        return parse_update(tokens)
    if cmd == "DELETE":
        return parse_delete(tokens)
    if cmd == "INDEX":
        return parse_index(tokens)
    if cmd == "JOIN":
        return parse_join(tokens)

    raise ParseError(f"Unsupported command: {cmd}")


# ---------------- CREATE ----------------
def parse_create(tokens):
    if len(tokens) < 4 or tokens[1] != "TABLE":
        raise ParseError("Usage: CREATE TABLE table (col TYPE, ...)")

    table = tokens[2]
    raw = " ".join(tokens[3:])
    match = re.search(r"\((.*)\)", raw)

    if not match:
        raise ParseError("Column definitions must be in parentheses")

    columns = []
    for col_def in match.group(1).split(","):
        parts = col_def.strip().split()
        if len(parts) != 2:
            raise ParseError(f"Invalid column definition: {col_def}")
        name, dtype = parts
        columns.append((name, dtype.upper()))

    return {
        "type": "CREATE_TABLE",
        "table": table,
        "columns": columns
    }


# ---------------- INSERT ----------------
def parse_insert(tokens):
    if tokens[1] != "INTO":
        raise ParseError("Expected INTO after INSERT")

    table = tokens[2]

    if "VALUES" not in tokens:
        raise ParseError("Expected VALUES")

    idx = tokens.index("VALUES")
    raw = " ".join(tokens[idx + 1:])
    match = re.search(r"\((.*)\)", raw)

    if not match:
        raise ParseError("VALUES must be enclosed in parentheses")

    values = [parse_value(v) for v in match.group(1).split(",")]

    return {
        "type": "INSERT",
        "table": table,
        "values": values
    }


# ---------------- SELECT ----------------
def parse_select(tokens):
    if "FROM" not in tokens:
        raise ParseError("SELECT must include FROM")

    from_idx = tokens.index("FROM")
    columns = tokens[1:from_idx]

    if not columns:
        raise ParseError("SELECT requires columns or *")

    table = tokens[from_idx + 1]

    where = []
    if "WHERE" in tokens:
        where_idx = tokens.index("WHERE")
        where_tokens = tokens[where_idx + 1:]
        where = parse_conditions(where_tokens)

    return {
        "type": "SELECT",
        "table": table,
        "columns": columns,
        "where": where
    }


# ---------------- UPDATE ----------------
def parse_update(tokens):
    table = tokens[1]

    if "SET" not in tokens:
        raise ParseError("UPDATE requires SET")

    set_idx = tokens.index("SET")

    if "WHERE" in tokens:
        where_idx = tokens.index("WHERE")
        set_tokens = tokens[set_idx + 1:where_idx]
        where_tokens = tokens[where_idx + 1:]
    else:
        set_tokens = tokens[set_idx + 1:]
        where_tokens = []

    updates = {}
    for item in set_tokens:
        if "=" not in item:
            raise ParseError("Invalid SET expression")
        col, val = item.split("=", 1)
        updates[col] = parse_value(val)

    where = parse_conditions(where_tokens) if where_tokens else []

    return {
        "type": "UPDATE",
        "table": table,
        "updates": updates,
        "where": where
    }


# ---------------- DELETE ----------------
def parse_delete(tokens):
    if tokens[1] != "FROM":
        raise ParseError("DELETE must be followed by FROM")

    table = tokens[2]

    where = []
    if "WHERE" in tokens:
        idx = tokens.index("WHERE")
        where = parse_conditions(tokens[idx + 1:])

    return {
        "type": "DELETE",
        "table": table,
        "where": where
    }


# ---------------- INDEX ----------------
def parse_index(tokens):
    if tokens[1] != "ON":
        raise ParseError("Usage: INDEX ON table column")

    table = tokens[2]
    column = tokens[3]

    return {
        "type": "CREATE_INDEX",
        "table": table,
        "column": column
    }


# ---------------- JOIN ----------------
def parse_join(tokens):
    """
    JOIN table1 table2 ON table1.col = table2.col
    """
    if "ON" not in tokens:
        raise ParseError("JOIN requires ON")

    left = tokens[1]
    right = tokens[2]

    on_idx = tokens.index("ON")
    condition = tokens[on_idx + 1]

    if "=" not in condition:
        raise ParseError("JOIN condition must use =")

    left_key, right_key = condition.split("=", 1)

    return {
        "type": "JOIN",
        "left_table": left,
        "right_table": right,
        "left_key": left_key,
        "right_key": right_key
    }
