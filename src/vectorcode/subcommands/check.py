import sys
from pathlib import Path

from vectorcode.cli_utils import CHECK_OPTIONS, Config, find_project_config_dir


async def check(configs: Config) -> int:
    assert isinstance(configs.check_item, str)
    assert configs.check_item.lower() in CHECK_OPTIONS
    match configs.check_item:
        case "config":
            project_local_config = await find_project_config_dir(".")
            if project_local_config is None:
                print("Failed!", file=sys.stderr)
                return 1
            else:
                print(str(Path(project_local_config).parent), end="")
    return 0
