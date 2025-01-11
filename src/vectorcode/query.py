import json
import sys

from pydantic import config
from vectorcode.common import get_client, get_embedding_function
from vectorcode.cli_utils import Config


from chromadb.errors import InvalidCollectionException
from vectorcode.common import get_collection_name


def query(configs: Config):
    client = get_client(configs)
    try:
        collection = client.get_collection(
            name=get_collection_name(str(configs.project_root)),
            embedding_function=get_embedding_function(configs),
        )
        collection_ef = collection.metadata.get("embedding_function")
        collection_ep = collection.metadata.get("embedding_params")
        if collection_ef and collection_ef != configs.embedding_function:
            print(f"The collection was embedded using {collection_ef}.")
            print(
                "Embeddings and query must use the same embedding function and parameters. Please double-check your config."
            )
            sys.exit(1)
        elif collection_ep and collection_ep != configs.embedding_params:
            print(
                f"The collection was embedded with a different set of configurations: {collection_ep}.",
                file=sys.stderr,
            )
            print("The result may be inaccurate.", file=sys.stderr)
    except (ValueError, InvalidCollectionException):
        print(f"There's no existing collection for {configs.project_root}")
        sys.exit(1)

    if not configs.pipe:
        print("Starting querying...")

    try:
        results = collection.query(
            query_texts=[configs.query or ""], n_results=configs.n_result
        )
    except IndexError:
        # no results found
        return
    if results["documents"] is None or len(results["documents"]) == 0:
        return

    structured_result = []

    for idx in range(len(results["ids"][0])):
        path = str(results["ids"][0][idx])
        document = results["documents"][0][idx]
        structured_result.append({"path": path, "document": document})

    if configs.pipe:
        print(json.dumps(structured_result))
    else:
        for idx, result in enumerate(structured_result):
            print(f"Path: {result['path']}")
            print(f"Content: \n{result['document']}")
            if idx != len(structured_result) - 1:
                print()
