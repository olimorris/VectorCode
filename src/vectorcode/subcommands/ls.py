import json
import os
import socket

import tabulate
from chromadb.api.types import IncludeEnum

from vectorcode.cli_utils import Config
from vectorcode.common import get_client


def ls(configs: Config) -> int:
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
        document_meta = collection.get(include=[IncludeEnum.metadatas])
        unique_files = set(
            i.get("path") for i in document_meta["metadatas"] if i is not None
        )
        result.append(
            {
                "project-root": meta["path"],
                "user": os.environ["USER"],
                "hostname": socket.gethostname(),
                "collection_name": collection_name,
                "size": collection.count(),
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
