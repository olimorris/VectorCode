import json
import os
from vectorcode.cli_utils import Config, expand_globs
from vectorcode.common import get_client, make_or_get_collection
import tqdm


def vectorise(configs: Config):
    client = get_client(configs)
    collection = make_or_get_collection(client, configs)
    files = expand_globs(configs.files or [], recursive=configs.recursive)

    stats = {
        "add": 0,
        "update": 0,
    }
    for file in tqdm.tqdm(files, total=len(files), disable=configs.pipe):
        with open(file) as fin:
            content = "".join(fin.readlines())

        if content:
            path_str = str(file)
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
