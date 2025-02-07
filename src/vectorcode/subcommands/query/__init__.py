import json
import os
import sys

from chromadb.api.types import IncludeEnum
from chromadb.errors import InvalidCollectionException, InvalidDimensionException

from vectorcode.chunking import StringChunker
from vectorcode.cli_utils import Config, expand_globs, expand_path
from vectorcode.common import (
    get_client,
    get_collection_name,
    get_embedding_function,
    verify_ef,
)


async def query(configs: Config) -> int:
    client = await get_client(configs)
    try:
        collection = await client.get_collection(
            name=get_collection_name(str(configs.project_root)),
            embedding_function=get_embedding_function(configs),
        )
        if not verify_ef(collection, configs):
            return 1
    except (ValueError, InvalidCollectionException):
        print(
            f"There's no existing collection for {configs.project_root}",
            file=sys.stderr,
        )
        return 1
    except InvalidDimensionException:
        print(
            "The collection was embedded with a different embedding model.",
            file=sys.stderr,
        )
        return 1
    except IndexError:
        print(
            "Failed to get the collection. Please check your config.", file=sys.stderr
        )
        return 1

    if not configs.pipe:
        print("Starting querying...")

    query_chunks = []
    if configs.query:
        chunker = StringChunker(configs.chunk_size, configs.overlap_ratio)
        for q in configs.query:
            query_chunks.extend(chunker.chunk(q))

    configs.query_exclude = [
        expand_path(i, True)
        for i in await expand_globs(configs.query_exclude)
        if os.path.isfile(i)
    ]
    if (await collection.count()) == 0:
        print("Empty collection!", file=sys.stderr)
        return 1
    try:
        num_query = await collection.count()
        if configs.query_multiplier > 0:
            num_query = int(configs.n_result * configs.query_multiplier)
        if len(configs.query_exclude):
            filtered_files = {"path": {"$nin": configs.query_exclude}}
        else:
            filtered_files = None
        results = await collection.query(
            query_texts=query_chunks,
            n_results=num_query,
            include=[
                IncludeEnum.metadatas,
                IncludeEnum.distances,
                IncludeEnum.documents,
            ],
            where=filtered_files,
        )
    except IndexError:
        # no results found
        return 0

    structured_result = []

    if configs.reranker is None:
        from .reranker import NaiveReranker

        aggregated_results = NaiveReranker(configs).rerank(results)
    else:
        from .reranker import CrossEncoderReranker

        aggregated_results = CrossEncoderReranker(
            configs, query_chunks, configs.reranker, **configs.reranker_params
        ).rerank(results)

    for path in aggregated_results:
        if os.path.isfile(path):
            with open(path) as fin:
                document = fin.read()
            if configs.use_absolute_path:
                output_path = os.path.abspath(path)
            else:
                output_path = os.path.relpath(path, configs.project_root)
            structured_result.append({"path": output_path, "document": document})
        else:
            print(
                f"{path} is no longer a valid file! Please re-run vectorcode vectorise to refresh the database.",
                file=sys.stderr,
            )

    if configs.pipe:
        print(json.dumps(structured_result))
    else:
        for idx, result in enumerate(structured_result):
            print(f"Path: {result['path']}")
            print(f"Content: \n{result['document']}")
            if idx != len(structured_result) - 1:
                print()
    return 0
