import sys
from vectorcode.common import get_client, get_collection_name
from vectorcode.cli_utils import Config
from chromadb.errors import InvalidCollectionException


def drop(config: Config):
    client = get_client(configs=config)
    try:
        collection = client.get_collection(
            name=get_collection_name(str(config.project_root))
        )
        collection_path = collection.metadata["path"]
        client.delete_collection(collection.name)
        print(f"Collection for {collection_path} has been deleted.")
    except (ValueError, InvalidCollectionException):
        print(f"There's no existing collection for {config.project_root}")
        sys.exit(1)
