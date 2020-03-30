HEADER_SIZE=8
def format_message(message):
    if not message:
        return None
    header = f'{len(message):<{HEADER_SIZE}}'
    return f'{header}{message}'