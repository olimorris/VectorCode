from vectorcode.cli_utils import Config
from vectorcode.common import get_client, get_collections


async def clean(configs: Config) -> int:
    client = await get_client(configs)
    async for collection in get_collections(client):
        meta = collection.metadata
        if await collection.count() == 0:
            await client.delete_collection(collection.name)
            if not configs.pipe:
                print(f"Deleted {meta['path']}.")

    return 0
