import io
import tarfile

import docker
from docker import DockerClient


def get_file_from_container(container_name: str, file_path: str) -> bytes:
    client = DockerClient(base_url="http://test-docker-daemon:2375")

    # Получаем ссылку на контейнер
    containers = client.containers.list(filters={
        'label': f'com.docker.compose.service={container_name}'
    })
    assert len(containers) == 1
    container = containers[0]

    # Проверяем, существует ли файл внутри контейнера
    try:
        # Получаем содержимое файла в виде архива tar
        stream, _ = container.get_archive(file_path)

        # Разархивируем файл
        file_data = b""
        with io.BytesIO() as f:
            for chunk in stream:
                f.write(chunk)
            f.seek(0)

            with tarfile.open(fileobj=f) as tar:
                member = tar.getmembers()[0]
                file_data = tar.extractfile(member).read()

        return file_data

    except docker.errors.NotFound:
        return None

    except (docker.errors.APIError, Exception) as e:
        return None
