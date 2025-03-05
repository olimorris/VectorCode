import asyncio
import hashlib
import json
import os
import sys
import uuid
from asyncio import Lock

import pathspec
import tabulate
import tqdm
from chromadb.api.models.AsyncCollection import AsyncCollection
from chromadb.api.types import IncludeEnum

from vectorcode.chunking import FileChunker
from vectorcode.cli_utils import Config, expand_globs, expand_path
from vectorcode.common import get_client, get_collection, verify_ef


def hash_str(string: str) -> str:
    """Return the sha-256 hash of a string."""
    return hashlib.sha256(string.encode()).hexdigest()


def get_uuid() -> str:
    return uuid.uuid4().hex


async def chunked_add(
    file_path: str,
    collection: AsyncCollection,
    collection_lock: Lock,
    stats: dict[str, int],
    stats_lock: Lock,
    configs: Config,
    max_batch_size: int,
):
    full_path_str = str(expand_path(str(file_path), True))
    async with collection_lock:
        num_existing_chunks = len(
            (
                await collection.get(
                    where={"path": full_path_str},
                    include=[IncludeEnum.metadatas],
                )
            )["ids"]
        )

    if num_existing_chunks:
        async with collection_lock:
            await collection.delete(where={"path": full_path_str})

    try:
        with open(full_path_str) as fin:
            chunks = list(
                FileChunker(configs.chunk_size, configs.overlap_ratio).chunk(fin)
            )
            if len(chunks) == 0 or (len(chunks) == 1 and chunks[0] == ""):
                # empty file
                return
            chunks.append(str(os.path.relpath(full_path_str, configs.project_root)))
            async with collection_lock:
                for idx in range(0, len(chunks), max_batch_size):
                    inserted_chunks = chunks[idx : idx + max_batch_size]
                    await collection.add(
                        ids=[get_uuid() for _ in inserted_chunks],
                        documents=inserted_chunks,
                        metadatas=[{"path": full_path_str} for _ in inserted_chunks],
                    )
    except UnicodeDecodeError:
        # probably binary. skip it.
        return

    if num_existing_chunks:
        async with stats_lock:
            stats["update"] += 1
    else:
        async with stats_lock:
            stats["add"] += 1


def show_stats(configs: Config, stats):
    if configs.pipe:
        print(json.dumps(stats))
    else:
        print(
            tabulate.tabulate(
                [
                    ["Added", "Updated", "Removed"],
                    [stats["add"], stats["update"], stats["removed"]],
                ],
                headers="firstrow",
            )
        )


async def vectorise(configs: Config) -> int:
    client = await get_client(configs)
    try:
        collection = await get_collection(client, configs, True)
    except IndexError:
        print("Failed to get/create the collection. Please check your config.")
        return 1
    if not verify_ef(collection, configs):
        return 1
    gitignore_path = os.path.join(str(configs.project_root), ".gitignore")
    files = await expand_globs(configs.files or [], recursive=configs.recursive)
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as fin:
            gitignore_spec = pathspec.GitIgnoreSpec.from_lines(fin.readlines())
        files = [
            file
            for file in files
            if (configs.force or not gitignore_spec.match_file(file))
        ]
    else:
        gitignore_spec = None

    stats = {"add": 0, "update": 0, "removed": 0}
    collection_lock = Lock()
    stats_lock = Lock()
    max_batch_size = await client.get_max_batch_size()

    with tqdm.tqdm(
        total=len(files), desc="Vectorising files...", disable=configs.pipe
    ) as bar:
        try:
            tasks = [
                asyncio.create_task(
                    chunked_add(
                        str(file),
                        collection,
                        collection_lock,
                        stats,
                        stats_lock,
                        configs,
                        max_batch_size,
                    )
                )
                for file in files
            ]
            for task in asyncio.as_completed(tasks):
                await task
                bar.update(1)
        except asyncio.CancelledError:
            print("Abort.", file=sys.stderr)
            return 1

    async with collection_lock:
        all_results = await collection.get(include=[IncludeEnum.metadatas])
        if all_results is not None and all_results.get("metadatas"):
            paths = (meta["path"] for meta in all_results["metadatas"])
            orphanes = set()
            for path in paths:
                if isinstance(path, str) and not os.path.isfile(path):
                    orphanes.add(path)
            async with stats_lock:
                stats["removed"] = len(orphanes)
            if len(orphanes):
                await collection.delete(where={"path": {"$in": list(orphanes)}})

    show_stats(configs=configs, stats=stats)
    return 0
