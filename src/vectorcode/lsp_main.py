import asyncio
import os
import time
import uuid
from pathlib import Path

from chromadb.api import AsyncClientAPI
from chromadb.api.models.AsyncCollection import AsyncCollection
from lsprotocol import types
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

cached_project_configs: dict[str, Config] = {}
cached_clients: dict[tuple[str, int], AsyncClientAPI] = {}
cached_collections: dict[str, AsyncCollection] = {}


async def lsp_start() -> int:
    server: LanguageServer = LanguageServer(
        name="vectorcode-server", version=__version__
    )

    @server.command("vectorcode")
    async def execute_command(ls: LanguageServer, *args):
        start_time = time.time()
        parsed_args = await parse_cli_args(args[0])
        assert parsed_args.action == CliAction.query
        if parsed_args.project_root is None:
            resolved_project_root = await find_project_config_dir(".")
            if resolved_project_root is not None:
                parsed_args.project_root = Path(resolved_project_root).parent.resolve()
            else:
                raise FileNotFoundError("Failed to automatically detect project root!")

        parsed_args.project_root = os.path.abspath(parsed_args.project_root)
        if cached_project_configs.get(parsed_args.project_root) is None:
            config_file = os.path.join(
                parsed_args.project_root, ".vectorcode", "config.json"
            )
            if not os.path.isfile(config_file):
                config_file = None
            cached_project_configs[parsed_args.project_root] = await load_config_file(
                config_file
            )
        final_configs = await cached_project_configs[
            parsed_args.project_root
        ].merge_from(parsed_args)
        progress_token = str(uuid.uuid4())
        await ls.progress.create_async(progress_token)
        ls.progress.begin(
            progress_token,
            types.WorkDoneProgressBegin(
                "VectorCode", message="Retrieving from VectorCode."
            ),
        )
        if not await try_server(final_configs.host, final_configs.port):
            raise ConnectionError(
                "Failed to find an existing ChromaDB server, which is a hard requirement for LSP mode!"
            )
        if cached_clients.get((final_configs.host, final_configs.port)) is None:
            cached_clients[(final_configs.host, final_configs.port)] = await get_client(
                final_configs
            )
        if cached_collections.get(str(final_configs.project_root)) is None:
            cached_collections[str(final_configs.project_root)] = await get_collection(
                cached_clients[(final_configs.host, final_configs.port)], final_configs
            )
        final_results = []
        for path in await get_query_result_files(
            collection=cached_collections[str(final_configs.project_root)],
            configs=final_configs,
        ):
            if os.path.isfile(path):
                with open(path) as fin:
                    final_results.append({"path": path, "document": fin.read()})
        ls.progress.end(
            progress_token,
            types.WorkDoneProgressEnd(
                message=f"Retrieved {len(final_results)} result{'s' if len(final_results) > 1 else ''} in {round(time.time() - start_time, 2)}s."
            ),
        )
        return final_results

    await asyncio.to_thread(server.start_io)
    return 0


def main():
    asyncio.run(lsp_start())


if __name__ == "__main__":
    main()
