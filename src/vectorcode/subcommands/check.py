import sys

from vectorcode.cli_utils import Config, find_project_config_dir


def check(configs: Config) -> int:
    match configs.check_item:
        case "config":
            project_local_config = find_project_config_dir(".")
            if project_local_config is None:
                print("Failed!", file=sys.stderr)
                return 1
    print("Passed!", file=sys.stderr)
    return 0
