import asyncio
import logging
import os
import sys
import traceback
from pathlib import Path

from vectorcode import __version__
from vectorcode.cli_utils import (
    CliAction,
    find_project_config_dir,
    load_config_file,
    parse_cli_args,
)
from vectorcode.common import start_server, try_server
from vectorcode.subcommands import (
    check,
    clean,
    drop,
    init,
    ls,
    query,
    update,
    vectorise,
)


async def async_main():
    cli_args = await parse_cli_args()
    if cli_args.no_stderr:
        sys.stderr = open(os.devnull, "w")
    project_dir = await find_project_config_dir(cli_args.project_root or ".")

    try:
        if project_dir is not None:
            if cli_args.project_root is None:
                cli_args.project_root = str(Path(project_dir).parent.resolve())

            project_config_file = os.path.join(
                cli_args.project_root, ".vectorcode", "config.json"
            )
            if os.path.isfile(project_config_file):
                # has project-local config. use it
                final_configs = await (
                    await load_config_file(project_config_file)
                ).merge_from(cli_args)
            else:
                # no project-local config. use global config.
                final_configs = await (await load_config_file()).merge_from(cli_args)
        else:
            final_configs = await (await load_config_file()).merge_from(cli_args)
            if final_configs.project_root is None:
                final_configs.project_root = "."
    except IOError as e:
        traceback.print_exception(e, file=sys.stderr)
        return 1

    match cli_args.action:
        case CliAction.check:
            return await check(cli_args)
        case CliAction.init:
            return await init(cli_args)
        case CliAction.version:
            print(__version__)
            return 0

    server_process = None
    if not await try_server(final_configs.host, final_configs.port):
        print(
            f"Host at {final_configs.host}:{final_configs.port} is unavailable. VectorCode will start its own Chromadb at a random port.",
            file=sys.stderr,
        )
        server_process = await start_server(final_configs)

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
            case CliAction.update:
                return_val = await update(final_configs)
            case CliAction.clean:
                return_val = await clean(final_configs)
    except Exception as e:
        return_val = 1
        traceback.print_exception(e, file=sys.stderr)
    finally:
        if server_process is not None:
            server_process.terminate()
            await server_process.wait()
        return return_val


def main():
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
