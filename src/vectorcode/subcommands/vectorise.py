import json
import os

import pathspec
import tqdm
from chromadb.api.types import IncludeEnum

from vectorcode.cli_utils import Config, expand_globs, expand_path
from vectorcode.common import get_client, make_or_get_collection, verify_ef


def vectorise(configs: Config) -> int:
    client = get_client(configs)
    collection = make_or_get_collection(client, configs)
    if not verify_ef(collection, configs):
        return 1
    files = expand_globs(configs.files or [], recursive=configs.recursive)

    gitignore_path = os.path.join(configs.project_root, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as fin:
            gitignore_spec = pathspec.GitIgnoreSpec.from_lines(fin.readlines())
    else:
        gitignore_spec = None

    stats = {"add": 0, "update": 0, "removed": 0}
    for file in tqdm.tqdm(files, total=len(files), disable=configs.pipe):
        if (
            (not configs.force)
            and gitignore_spec is not None
            and gitignore_spec.match_file(file)
        ):
            # handles gitignore.
            continue
        with open(file) as fin:
            content = "".join(fin.readlines())

        if content:
            path_str = str(expand_path(str(file), True))
            if len(collection.get(where={"path": path_str})["ids"]):
                collection.update(
                    ids=[path_str], documents=[content], metadatas=[{"path": path_str}]
                )
                stats["update"] += 1
            else:
                collection.add(
                    [path_str], documents=[content], metadatas=[{"path": path_str}]
                )
                stats["add"] += 1

    all_results = collection.get(include=[IncludeEnum.metadatas])
    if all_results is not None and all_results.get("metadatas"):
        for idx in range(len(all_results["ids"])):
            path_in_meta = str(all_results["metadatas"][idx].get("path"))
            if path_in_meta is not None and not os.path.isfile(path_in_meta):
                collection.delete(where={"path": path_in_meta})
                stats["removed"] += 1

    if configs.pipe:
        print(json.dumps(stats))
    else:
        print(f"Added:\t{stats['add']}")
        print(f"Updated:\t{stats['update']}")
        if stats["removed"]:
            print(f"Removed orphanes:\t{stats['removed']}")
    return 0
