import asyncio
import logging
import os
import signal
from typing import Optional

import httpx
from chromadb.api import AsyncClientAPI

from vectorcode import __version__
from vectorcode.cli_utils import (
    CliAction,
    cli_arg_parser,
    find_project_config_dir,
    load_config_file,
)
from vectorcode.common import get_client, start_server
from vectorcode.subcommands import check, drop, init, ls, query, vectorise


def main():
    cli_args = cli_arg_parser()
    match cli_args.action:
        case CliAction.check:
            return check(cli_args)
    project_config_dir = find_project_config_dir(cli_args.project_root)

    if project_config_dir is not None:
        project_config_file = os.path.join(project_config_dir, "config.json")
        if os.path.isfile(project_config_file):
            final_configs = load_config_file(project_config_file).merge_from(cli_args)
        else:
            final_configs = cli_args
    else:
        final_configs = load_config_file().merge_from(cli_args)

    server_process = None
    client: Optional[AsyncClientAPI] = None
    try:
        client = asyncio.run(get_client(final_configs))
    except httpx.ConnectError:
        server_process = start_server(final_configs)

    if client is None:
        client = asyncio.run(get_client(final_configs))

    if final_configs.pipe:
        # NOTE: NNCF (intel GPU acceleration for sentence transformer) keeps showing logs.
        # This disables logs below ERROR so that it doesn't hurt the `pipe` output.
        logging.disable(logging.ERROR)

    return_val = 0
    try:
        match final_configs.action:
            case CliAction.query:
                return_val = asyncio.run(query(final_configs, client))
            case CliAction.vectorise:
                return_val = asyncio.run(vectorise(final_configs, client))
            case CliAction.drop:
                return_val = asyncio.run(drop(final_configs, client))
            case CliAction.ls:
                return_val = asyncio.run(ls(final_configs, client))
            case CliAction.init:
                return_val = asyncio.run(init(final_configs))
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
