from docker import APIClient
from docker.models.containers import Container


def retrieve_all_docker_containers() -> list[Container]:
    d = APIClient(
        base_url="http://test-docker-daemon:2375",
    )
    return d.containers(all=True)


def no_docker_containers():
    d = APIClient(
        base_url="http://test-docker-daemon:2375",
    )
    for container in retrieve_all_docker_containers():
        d.stop(container['Id'])
        d.remove_container(container['Id'])
