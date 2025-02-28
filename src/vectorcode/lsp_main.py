import asyncio
import os
from pathlib import Path

from chromadb.api import AsyncClientAPI
from chromadb.api.models.AsyncCollection import AsyncCollection
from pygls.server import LanguageServer

from vectorcode import __version__
from vectorcode.cli_utils import (
    CliAction,
    Config,
    find_project_config_dir,
    load_config_file,
    parse_cli_args,
)
from vectorcode.common import get_client, get_collection, try_server
from vectorcode.subcommands.query import get_query_result_files

project_configs: dict[str, Config] = {}
clients: dict[tuple[str, int], AsyncClientAPI] = {}
collections: dict[str, AsyncCollection] = {}


async def lsp_start() -> int:
    server: LanguageServer = LanguageServer(
        name="vectorcode-server", version=__version__
    )

    print(f"Started {server}")

    @server.command("vectorcode")
    async def execute_command(ls: LanguageServer, *args):
        parsed_args = await parse_cli_args(args[0])
        assert parsed_args.action == CliAction.query
        if parsed_args.project_root is None:
            parsed_args.project_root = (
                Path(await find_project_config_dir(".") or ".").parent.resolve() or "."
            )
        parsed_args.project_root = os.path.abspath(parsed_args.project_root)
        if project_configs.get(parsed_args.project_root) is None:
            config_file = os.path.join(
                parsed_args.project_root, ".vectorcode", "config.json"
            )
            if not os.path.isfile(config_file):
                config_file = None
            project_configs[parsed_args.project_root] = await load_config_file(
                config_file
            )
        final_configs = await project_configs[parsed_args.project_root].merge_from(
            parsed_args
        )
        if not await try_server(final_configs.host, final_configs.port):
            raise ConnectionError(
                "Failed to find an existing ChromaDB server, which is a hard requirement for LSP mode!"
            )
        if clients.get((final_configs.host, final_configs.port)) is None:
            clients[(final_configs.host, final_configs.port)] = await get_client(
                final_configs
            )
        if collections.get(str(final_configs.project_root)) is None:
            collections[str(final_configs.project_root)] = await get_collection(
                clients[(final_configs.host, final_configs.port)], final_configs
            )
        final_results = []
        for path in await get_query_result_files(
            collection=collections[str(final_configs.project_root)],
            configs=final_configs,
        ):
            with open(path) as fin:
                final_results.append({"path": path, "document": fin.read()})

        return final_results

    await asyncio.to_thread(server.start_io)
    return 0


def main():
    asyncio.run(lsp_start())


if __name__ == "__main__":
    main()
