from uuid import UUID


def release_mark(release_id: str | UUID):
    return {
        "x-release-id": str(release_id),
    }
