import asyncio
import logging
import os
import signal
from pathlib import Path

from vectorcode import __version__
from vectorcode.cli_utils import (
    CliAction,
    cli_arg_parser,
    find_project_config_dir,
    load_config_file,
)
from vectorcode.common import start_server, try_server
from vectorcode.subcommands import check, drop, init, ls, query, vectorise


async def async_main():
    cli_args = await cli_arg_parser()
    match cli_args.action:
        case CliAction.check:
            return await check(cli_args)
    project_config_dir = await find_project_config_dir(cli_args.project_root or ".")

    if project_config_dir is not None:
        if cli_args.project_root is None:
            cli_args.project_root = str(Path(project_config_dir).parent.resolve())

        project_config_file = os.path.join(project_config_dir, "config.json")
        if os.path.isfile(project_config_file):
            final_configs = await (
                await load_config_file(project_config_file)
            ).merge_from(cli_args)
        else:
            final_configs = cli_args
    else:
        final_configs = await (await load_config_file()).merge_from(cli_args)
        if final_configs.project_root is None:
            final_configs.project_root = "."

    server_process = None
    if not try_server(final_configs.host, final_configs.port):
        server_process = start_server(final_configs)

    if final_configs.pipe:
        # NOTE: NNCF (intel GPU acceleration for sentence transformer) keeps showing logs.
        # This disables logs below ERROR so that it doesn't hurt the `pipe` output.
        logging.disable(logging.ERROR)

    return_val = 0
    try:
        match final_configs.action:
            case CliAction.query:
                return_val = await query(final_configs)
            case CliAction.vectorise:
                return_val = await vectorise(final_configs)
            case CliAction.drop:
                return_val = await drop(final_configs)
            case CliAction.ls:
                return_val = await ls(final_configs)
            case CliAction.init:
                return_val = await init(final_configs)
            case CliAction.version:
                print(__version__)
                return_val = 0
    except Exception:
        return_val = 1
    finally:
        if server_process is not None:
            try:
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        return return_val


def main():
    return asyncio.run(async_main())
