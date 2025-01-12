from vectorcode.cli_utils import CliAction, load_config_file, cli_arg_parser
from vectorcode.query import query
from vectorcode.vectorise import vectorise
from vectorcode.drop import drop
from vectorcode.ls import ls


def main():
    cli_args = cli_arg_parser()
    config_file_configs = load_config_file()
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
    return return_val
