def parse(command):
    tokens = command.strip().split()

    if not tokens:
        return None

    cmd = tokens[0].upper()

    if cmd == "CREATE":
        return ("CREATE", tokens)
    if cmd == "INSERT":
        return ("INSERT", tokens)
    if cmd == "SELECT":
        return ("SELECT", tokens)
    if cmd == "INDEX":
        return ("INDEX", tokens)
    if cmd == "JOIN":
        return ("JOIN", tokens)

    raise ValueError("Unsupported command")
