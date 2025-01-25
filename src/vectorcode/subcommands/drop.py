from chromadb.errors import InvalidCollectionException

from vectorcode.cli_utils import Config
from vectorcode.common import get_client, get_collection_name


async def drop(config: Config) -> int:
    client = await get_client(config)
    try:
        collection = await client.get_collection(
            name=get_collection_name(str(config.project_root))
        )
        collection_path = collection.metadata["path"]
        await client.delete_collection(collection.name)
        print(f"Collection for {collection_path} has been deleted.")
        return 0
    except (ValueError, InvalidCollectionException):
        print(f"There's no existing collection for {config.project_root}")
        return 1
