import json

from chromadb.api.types import IncludeEnum
from chromadb.errors import InvalidCollectionException, InvalidDimensionException

from vectorcode.cli_utils import Config
from vectorcode.common import (
    get_client,
    get_collection_name,
    get_embedding_function,
    verify_ef,
)


def query(configs: Config) -> int:
    client = get_client(configs)
    try:
        collection = client.get_collection(
            name=get_collection_name(str(configs.project_root)),
            embedding_function=get_embedding_function(configs),
        )
        if not verify_ef(collection, configs):
            return 1
    except (ValueError, InvalidCollectionException):
        print(f"There's no existing collection for {configs.project_root}")
        return 1
    except InvalidDimensionException:
        print("The collection was embedded with a different embedding model.")
        return 1

    if not configs.pipe:
        print("Starting querying...")

    try:
        results = collection.query(
            query_texts=[configs.query or ""],
            n_results=configs.n_result,
            include=[IncludeEnum.metadatas, IncludeEnum.distances],
        )
    except IndexError:
        # no results found
        return 0

    structured_result = []

    for idx in range(len(results["ids"][0])):
        path = str(results["metadatas"][0][idx]["path"])
        with open(path) as fin:
            document = "".join(fin.readlines())
        structured_result.append({"path": path, "document": document})

    if configs.pipe:
        print(json.dumps(structured_result))
    else:
        for idx, result in enumerate(structured_result):
            print(f"Path: {result['path']}")
            print(f"Content: \n{result['document']}")
            if idx != len(structured_result) - 1:
                print()
    return 0
