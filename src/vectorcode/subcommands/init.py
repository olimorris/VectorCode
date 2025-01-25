import os
import shutil
import sys

from vectorcode.cli_utils import GLOBAL_CONFIG_PATH, Config


async def init(configs: Config) -> int:
    project_config_dir = os.path.join(str(configs.project_root), ".vectorcode")
    if os.path.isdir(project_config_dir):
        print(
            f"{configs.project_root} is already initialised for VectorCode.",
            file=sys.stderr,
        )
        return 1
    os.makedirs(project_config_dir)
    print(f"VectorCode project root has been initialised at {configs.project_root}")
    if os.path.isfile(GLOBAL_CONFIG_PATH):
        shutil.copyfile(
            GLOBAL_CONFIG_PATH, os.path.join(project_config_dir, "config.json")
        )
        print(
            "The global configuration at ~/.config/vectorcode/config.json has been copied to the project config directory."
        )
    print(
        "Note: The collection in the database will not be created until you vectorise a file."
    )
    return 0
