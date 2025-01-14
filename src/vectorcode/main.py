import os
from pathlib import Path
from vectorcode.cli_utils import (
    CliAction,
    find_project_config_dir,
    load_config_file,
    cli_arg_parser,
)
from vectorcode.init import init
from vectorcode.query import query
from vectorcode.vectorise import vectorise
from vectorcode.drop import drop
from vectorcode.ls import ls


def main():
    cli_args = cli_arg_parser()
    config_file_configs = load_config_file()
    project_config_dir = find_project_config_dir(cli_args.project_root)

    if project_config_dir is not None:
        project_config_file = os.path.join(project_config_dir, "config.json")
        print(project_config_dir)
        if os.path.isfile(project_config_file):
            config_file_configs = config_file_configs.merge_from(
                load_config_file(project_config_file)
            )
    final_configs = config_file_configs.merge_from(cli_args)

    return_val = 0
    match final_configs.action:
        case CliAction.query:
            return_val = query(final_configs)
        case CliAction.vectorise:
            return_val = vectorise(final_configs)
        case CliAction.drop:
            return_val = drop(final_configs)
        case CliAction.ls:
            return_val = ls(final_configs)
        case CliAction.init:
            return_val = init(final_configs)
    return return_val
