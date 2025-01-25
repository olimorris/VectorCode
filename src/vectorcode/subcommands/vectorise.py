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
from chromadb.api.types import IncludeEnum

from vectorcode.chunking import FileChunker
from vectorcode.cli_utils import Config, expand_globs, expand_path
from vectorcode.common import get_client, make_or_get_collection, verify_ef


def hash_str(string: str) -> str:
    """Return the sha-256 hash of a string."""
    return hashlib.sha256(string.encode()).hexdigest()


def get_uuid() -> str:
    return uuid.uuid4().hex


async def vectorise(configs: Config) -> int:
    client = await get_client(configs)
    collection = await make_or_get_collection(client, configs)
    if not verify_ef(collection, configs):
        return 1
    files = await expand_globs(configs.files or [], recursive=configs.recursive)

    gitignore_path = os.path.join(str(configs.project_root), ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as fin:
            gitignore_spec = pathspec.GitIgnoreSpec.from_lines(fin.readlines())
    else:
        gitignore_spec = None

    stats = {"add": 0, "update": 0, "removed": 0}
    collection_lock = Lock()
    stats_lock = Lock()
    max_batch_size = await client.get_max_batch_size()

    async def chunked_add(file_path: str):
        if (
            (not configs.force)
            and gitignore_spec is not None
            and gitignore_spec.match_file(file_path)
        ):
            # handles gitignore.
            return

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
            async with stats_lock:
                stats["update"] += 1
        else:
            async with stats_lock:
                stats["add"] += 1
        with open(full_path_str) as fin:
            chunks = list(
                FileChunker(configs.chunk_size, configs.overlap_ratio).chunk(fin)
            )
            async with collection_lock:
                for idx in range(0, len(chunks), max_batch_size):
                    inserted_chunks = chunks[idx : idx + max_batch_size]
                    await collection.add(
                        ids=[get_uuid() for _ in inserted_chunks],
                        documents=inserted_chunks,
                        metadatas=[{"path": full_path_str} for _ in inserted_chunks],
                    )

    with tqdm.tqdm(
        total=len(files), desc="Vectorising files...", disable=configs.pipe
    ) as bar:
        try:
            tasks = [asyncio.create_task(chunked_add(str(file))) for file in files]
            for task in asyncio.as_completed(tasks):
                await task
                bar.update(1)
        except asyncio.CancelledError:
            print("Abort.", file=sys.stderr)
            return 1

    all_results = await collection.get(include=[IncludeEnum.metadatas])
    if all_results is not None and all_results.get("metadatas"):
        for idx in range(len(all_results["ids"])):
            path_in_meta = str(all_results["metadatas"][idx].get("path"))
            if path_in_meta is not None and not os.path.isfile(path_in_meta):
                await collection.delete(where={"path": path_in_meta})
                stats["removed"] += 1

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
    return 0
