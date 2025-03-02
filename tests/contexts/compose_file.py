from pathlib import Path

import vedro


def _make_compose_file(filename: str, content: str):
    root = Path('/project')
    file_path = root / (Path(filename).parent)

    file_path.mkdir(parents=True, exist_ok=True)

    with open(root / filename, 'w') as file:
        file.write(content)

    vedro.defer(cleanup_compose_files)
    return filename


def cleanup_compose_files():
    skip_filename = 'docker-compose.default.yaml'
    for file in sorted(Path('/project').rglob('*'), key=lambda x: len(str(x)), reverse=True):
        if file.name == skip_filename:
            continue
        if file.is_file():
            file.unlink(missing_ok=True)
        elif file.is_dir():
            file.rmdir()
    if not (root := Path('/project')/skip_filename).exists():
        _make_compose_file(
            skip_filename,
            '''
version: "3"

services:
  eeeeeeeee2:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
'''
                           )


def compose_file(filename: str, content: str):
    _make_compose_file(filename, content)
    vedro.defer(cleanup_compose_files)
    return filename
