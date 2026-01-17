import shlex
import re

class ParseError(Exception):
    pass

KEYWORDS = {
    "CREATE", "TABLE", "INSERT", "INTO", "VALUES",
    "SELECT", "FROM", "WHERE",
    "UPDATE", "SET", "DELETE",
    "INDEX", "ON", "JOIN"
}

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
    if tokens[1] != "TABLE":
        raise ParseError("Expected TABLE")

    table = tokens[2]
    raw_cols = " ".join(tokens[3:])
    match = re.search(r"\((.*)\)", raw_cols)
    if not match:
        raise ParseError("Column definitions required")

    columns = []
    for col_def in match.group(1).split(","):
        parts = col_def.strip().split()
        if len(parts) != 2:
            raise ParseError(f"Invalid column definition: {col_def}")
        col_name, col_type = parts
        columns.append((col_name, col_type.upper()))

    return {"type": "CREATE", "table": table, "columns": columns}

# ---------------- INSERT ----------------
def parse_insert(tokens):
    if tokens[1] != "INTO":
        raise ParseError("Expected INTO")
    table = tokens[2]

    if "VALUES" not in tokens:
        raise ParseError("Expected VALUES")
    idx = tokens.index("VALUES")
    raw_values = " ".join(tokens[idx+1:])
    match = re.search(r"\((.*)\)", raw_values)
    if not match:
        raise ParseError("VALUES must be in parentheses")

    values = []
    for v in match.group(1).split(","):
        v = v.strip()
        if v.startswith("'") and v.endswith("'"):
            values.append(v[1:-1])
        else:
            try:
                values.append(int(v))
            except:
                try:
                    values.append(float(v))
                except:
                    values.append(v)
    return {"type": "INSERT", "table": table, "values": values}

# ---------------- SELECT ----------------
def parse_select(tokens):
    if tokens[1] != "*":
        raise ParseError("Only SELECT * supported")
    if tokens[2] != "FROM":
        raise ParseError("Expected FROM")
    table = tokens[3]
    where = None
    if "WHERE" in tokens:
        idx = tokens.index("WHERE")
        col, val = tokens[idx+1].split("=")
        val = val.strip()
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        else:
            try:
                val = int(val)
            except:
                try:
                    val = float(val)
                except:
                    pass
        where = {col: val}
    return {"type": "SELECT", "table": table, "where": where}

# ---------------- UPDATE ----------------
def parse_update(tokens):
    table = tokens[1]
    if "SET" not in tokens:
        raise ParseError("Expected SET")
    set_idx = tokens.index("SET")
    set_col, set_val = tokens[set_idx+1].split("=")
    val = set_val.strip()
    if val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    else:
        try:
            val = int(val)
        except:
            try:
                val = float(val)
            except:
                pass
    set_dict = {set_col: val}

    where_dict = None
    if "WHERE" in tokens:
        where_idx = tokens.index("WHERE")
        col, val = tokens[where_idx+1].split("=")
        val = val.strip()
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        else:
            try:
                val = int(val)
            except:
                try:
                    val = float(val)
                except:
                    pass
        where_dict = {col: val}

    return {"type": "UPDATE", "table": table, "set": set_dict, "where": where_dict}

# ---------------- DELETE ----------------
def parse_delete(tokens):
    if tokens[1] != "FROM":
        raise ParseError("Expected FROM")
    table = tokens[2]
    where_dict = None
    if "WHERE" in tokens:
        idx = tokens.index("WHERE")
        col, val = tokens[idx+1].split("=")
        val = val.strip()
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        else:
            try:
                val = int(val)
            except:
                try:
                    val = float(val)
                except:
                    pass
        where_dict = {col: val}
    return {"type": "DELETE", "table": table, "where": where_dict}

# ---------------- INDEX ----------------
def parse_index(tokens):
    if tokens[1] != "ON":
        raise ParseError("Expected ON")
    table = tokens[2]
    column = tokens[3]
    return {"type": "INDEX", "table": table, "column": column}

# ---------------- JOIN ----------------
def parse_join(tokens):
    left = tokens[1]
    right = tokens[2]
    left_key = tokens[3]
    right_key = tokens[4]
    return {"type": "JOIN", "left_table": left, "right_table": right,
            "left_key": left_key, "right_key": right_key}
