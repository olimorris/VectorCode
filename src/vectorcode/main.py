from vectorcode.cli_utils import CliAction, load_config_file, cli_arg_parser
from vectorcode.query import query
from vectorcode.vectorise import vectorise
from vectorcode.drop import drop
from vectorcode.ls import ls


def main():
    cli_args = cli_arg_parser()
    config_file_configs = load_config_file()
    final_configs = config_file_configs.merge_from(cli_args)

    match final_configs.action:
        case CliAction.query:
            query(final_configs)
        case CliAction.vectorise:
            vectorise(final_configs)
        case CliAction.drop:
            drop(final_configs)
        case CliAction.ls:
            ls(final_configs)
