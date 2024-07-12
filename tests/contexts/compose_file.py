from pathlib import Path


def compose_file(filename: str, content: str):
    with open(Path('/compose-files') / filename, 'w') as file:
        file.write(content)
    return filename
