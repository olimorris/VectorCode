import json
import os
import socket
from vectorcode.cli_utils import Config
from vectorcode.common import get_client


def ls(configs: Config):
    client = get_client(configs)
    result: list[dict] = []
    for collection_name in client.list_collections():
        collection = client.get_collection(collection_name)
        meta = collection.metadata
        if meta is None:
            continue
        if meta.get("created-by") != "VectorCode":
            continue
        if meta.get("username") != os.environ["USER"]:
            continue
        if meta.get("hostname") != socket.gethostname():
            continue
        result.append(
            {
                "project-root": meta["path"],
                "user": os.environ["USER"],
                "hostname": socket.gethostname(),
                "collection_name": collection_name,
                "size": collection.count(),
            }
        )

    if configs.pipe:
        print(json.dumps(result))
    else:
        for meta in result:
            print(f"Collection with project root: {meta['project-root']}")
