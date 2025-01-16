import json
from collections import defaultdict
from typing import DefaultDict

from chromadb.api.types import IncludeEnum, QueryResult
from chromadb.errors import InvalidCollectionException, InvalidDimensionException

from vectorcode.chunking import StringChunker
from vectorcode.cli_utils import Config
from vectorcode.common import (
    get_client,
    get_collection_name,
    get_embedding_function,
    verify_ef,
)


def top_k_results(results: QueryResult, configs: Config) -> list[str]:
    assert results["metadatas"] is not None
    assert results["distances"] is not None
    documents: DefaultDict[str, list[float]] = defaultdict(list)
    for query_chunk_idx in range(len(results["ids"])):
        chunk_metas = results["metadatas"][query_chunk_idx]
        chunk_distances = results["distances"][query_chunk_idx]
        paths = [str(meta["path"]) for meta in chunk_metas]
        assert len(paths) == len(chunk_distances)
        for distance, path in zip(chunk_distances, paths):
            documents[path].append(distance)

    doc_list = sorted(
        documents.keys(), key=lambda x: sum(documents[x]) / len(documents[x])
    )
    return doc_list[: configs.n_result]


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

    query_chunks = list(
        StringChunker(configs.chunk_size, configs.overlap_ratio).chunk(
            configs.query or ""
        )
    )
    try:
        num_query = collection.count()
        if configs.query_multiplier > 0:
            num_query = configs.n_result * configs.query_multiplier
        results = collection.query(
            query_texts=query_chunks,
            n_results=num_query,
            include=[IncludeEnum.metadatas, IncludeEnum.distances],
        )
    except IndexError:
        # no results found
        return 0

    structured_result = []
    aggregated_results = top_k_results(results, configs)
    for path in aggregated_results:
        with open(path) as fin:
            document = fin.read()
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
