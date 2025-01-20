import json
import os
import socket
from typing import Any, Coroutine

import tabulate
from chromadb.api import AsyncClientAPI
from chromadb.api.types import IncludeEnum

from vectorcode.cli_utils import Config


async def ls(configs: Config, client_co: Coroutine[Any, Any, AsyncClientAPI]) -> int:
    client = await client_co
    result: list[dict] = []
    collections = await client.list_collections()
    for collection_name in collections:
        collection = await client.get_collection(collection_name)
        meta = collection.metadata
        if meta is None:
            continue
        if meta.get("created-by") != "VectorCode":
            continue
        if meta.get("username") != os.environ["USER"]:
            continue
        if meta.get("hostname") != socket.gethostname():
            continue
        document_meta = await collection.get(include=[IncludeEnum.metadatas])
        unique_files = set(
            i.get("path") for i in document_meta["metadatas"] if i is not None
        )
        result.append(
            {
                "project-root": meta["path"],
                "user": os.environ["USER"],
                "hostname": socket.gethostname(),
                "collection_name": collection_name,
                "size": await collection.count(),
                "embedding_function": meta["embedding_function"],
                "num_files": len(unique_files),
            }
        )

    if configs.pipe:
        print(json.dumps(result))
    else:
        table = []
        for meta in result:
            row = [
                meta["project-root"].replace(os.environ["HOME"], "~"),
                meta["size"],
                meta["num_files"],
                meta["embedding_function"],
            ]
            table.append(row)
        print(
            tabulate.tabulate(
                table,
                headers=[
                    "Project Root",
                    "Collection Size",
                    "Number of Files",
                    "Embedding Function",
                ],
            )
        )
    return 0
