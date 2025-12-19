def remove_colors(text: str) -> str:
    import re
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def create_pool_file(base_path: str, addr: bytes) -> None:
    with open(base_path + ".addr", 'wb') as f:
        f.write(addr)
