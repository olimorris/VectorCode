import json
import pathspec
import os
from vectorcode.cli_utils import Config, expand_globs, expand_path
from vectorcode.common import get_client, make_or_get_collection, verify_ef
import tqdm


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

    stats = {
        "add": 0,
        "update": 0,
    }
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
            if len(collection.get(ids=[path_str])["ids"]):
                collection.update(ids=[path_str], documents=[content])
                stats["update"] += 1
            else:
                collection.add([path_str], documents=[content])
                stats["add"] += 1

    orphaned = [path for path in collection.get()["ids"] if not os.path.isfile(path)]
    if orphaned:
        collection.delete(ids=orphaned)
    if configs.pipe:
        stats["removed"] = len(orphaned)
        print(json.dumps(stats))
    else:
        print(f"Added:\t{stats['add']}")
        print(f"Updated:\t{stats['update']}")
        if orphaned:
            print(f"Removed orphanes:\t{len(orphaned)}")
    return 0
