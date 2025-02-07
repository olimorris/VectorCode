import argparse
import glob
import json
import os
import sys
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import shtab

from vectorcode import __version__

PathLike = Union[str, Path]

GLOBAL_CONFIG_PATH = os.path.join(
    os.path.expanduser("~"), ".config", "vectorcode", "config.json"
)

CHECK_OPTIONS = ["config"]


class CliAction(Enum):
    vectorise = "vectorise"
    query = "query"
    drop = "drop"
    ls = "ls"
    init = "init"
    version = "version"
    check = "check"
    update = "update"


@dataclass
class Config:
    recursive: bool = False
    to_be_deleted: list[str] = field(default_factory=list)
    pipe: bool = False
    action: Optional[CliAction] = None
    files: list[PathLike] = field(default_factory=list)
    project_root: Optional[PathLike] = None
    query: Optional[list[str]] = None
    host: str = "127.0.0.1"
    port: int = 8000
    embedding_function: str = "SentenceTransformerEmbeddingFunction"  # This should fallback to whatever the default is.
    embedding_params: dict[str, Any] = field(default_factory=(lambda: {}))
    n_result: int = 1
    force: bool = False
    db_path: Optional[str] = "~/.local/share/vectorcode/chromadb/"
    db_settings: Optional[dict] = None
    chunk_size: int = -1
    overlap_ratio: float = 0.2
    query_multiplier: int = -1
    query_exclude: list[PathLike] = field(default_factory=list)
    reranker: Optional[str] = None
    reranker_params: dict[str, Any] = field(default_factory=dict)
    check_item: Optional[str] = None
    use_absolute_path: bool = False

    @classmethod
    async def import_from(cls, config_dict: dict[str, Any]) -> "Config":
        db_path = config_dict.get("db_path")
        host = config_dict.get("host") or "localhost"
        port = config_dict.get("port") or 8000
        if db_path is None:
            db_path = os.path.expanduser("~/.local/share/vectorcode/chromadb/")
        elif not os.path.isdir(db_path):
            print(
                f"{str(db_path)} is not a valid directory!",
                file=sys.stderr,
            )
            sys.exit(1)
        return Config(
            **{
                "embedding_function": config_dict.get(
                    "embedding_function", "SentenceTransformerEmbeddingFunction"
                ),
                "embedding_params": config_dict.get("embedding_params", {}),
                "host": host,
                "port": port,
                "db_path": db_path,
                "chunk_size": config_dict.get("chunk_size", -1),
                "overlap_ratio": config_dict.get("overlap_ratio", 0.2),
                "query_multiplier": config_dict.get("query_multiplier", -1),
                "reranker": config_dict.get("reranker", None),
                "reranker_params": config_dict.get("reranker_params", {}),
                "db_settings": config_dict.get("db_settings", None),
            }
        )

    async def merge_from(self, other: "Config") -> "Config":
        """Return the merged config."""
        final_config = {}
        default_config = Config()
        for merged_field in fields(self):
            final_config[merged_field.name] = getattr(other, merged_field.name)
            if not final_config[merged_field.name] or final_config[
                merged_field.name
            ] == getattr(default_config, merged_field.name):
                final_config[merged_field.name] = getattr(self, merged_field.name)
        return Config(**final_config)


async def cli_arg_parser():
    shared_parser = argparse.ArgumentParser(add_help=False)
    chunkinng_parser = argparse.ArgumentParser(add_help=False)
    chunkinng_parser.add_argument(
        "--overlap", "-o", type=float, help="Ratio of overlaps between chunks."
    )
    chunkinng_parser.add_argument(
        "-c",
        "--chunk_size",
        type=int,
        default=-1,
        help="Size of chunks (-1 for no chunking).",
    )
    shared_parser.add_argument(
        "--project_root",
        default=None,
        help="Project root to be used as an identifier of the project.",
    ).complete = shtab.DIRECTORY
    shared_parser.add_argument(
        "--pipe",
        "-p",
        action="store_true",
        default=False,
        help="Print structured output for other programs to process.",
    )
    main_parser = argparse.ArgumentParser(
        "vectorcode",
        parents=[shared_parser],
        description=f"VectorCode {__version__}: A CLI RAG utility.",
    )
    shtab.add_argument_to(
        main_parser,
        ["-s", "--print-completion"],
        parent=main_parser,
        help="Print completion script.",
    )
    subparsers = main_parser.add_subparsers(
        dest="action",
        required=False,
        title="subcommands",
    )
    subparsers.add_parser("ls", parents=[shared_parser], help="List all collections.")

    vectorise_parser = subparsers.add_parser(
        "vectorise",
        parents=[shared_parser, chunkinng_parser],
        help="Vectorise and send documents to chromadb.",
    )
    vectorise_parser.add_argument(
        "file_paths", nargs="+", help="Paths to files to be vectorised."
    ).complete = shtab.FILE
    vectorise_parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=False,
        help="Recursive indexing for directories.",
    )
    vectorise_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        default=False,
        help="Force to vectorise the file(s) against the gitignore.",
    )

    query_parser = subparsers.add_parser(
        "query",
        parents=[shared_parser, chunkinng_parser],
        help="Send query to retrieve documents.",
    )
    query_parser.add_argument("query", nargs="+", help="Query keywords.")
    query_parser.add_argument(
        "--multiplier", "-m", type=int, default=-1, help="Query multiplier."
    )
    query_parser.add_argument(
        "-n", "--number", type=int, default=1, help="Number of results to retrieve."
    )
    query_parser.add_argument(
        "--exclude", nargs="*", help="Files to exclude from query results."
    ).complete = shtab.FILE
    query_parser.add_argument(
        "--absolute",
        default=False,
        action="store_true",
        help="Use absolute path when returning the retrieval results.",
    )

    subparsers.add_parser("drop", parents=[shared_parser], help="Remove a collection.")

    subparsers.add_parser(
        "init",
        parents=[shared_parser],
        help="Initialise a directory as VectorCode project root.",
    )

    subparsers.add_parser(
        "version", parents=[shared_parser], help="Print the version number."
    )
    check_parser = subparsers.add_parser(
        "check", parents=[shared_parser], help="Check for project-local setup."
    )

    check_parser.add_argument(
        "check_item",
        choices=CHECK_OPTIONS,
        type=str,
        help=f"Item to be checked. Possible options: [{', '.join(CHECK_OPTIONS)}]",
    )

    subparsers.add_parser(
        "update",
        parents=[shared_parser],
        help="Update embeddings in the database for indexed files.",
    )

    main_args = main_parser.parse_args()
    if main_args.action is None:
        main_args = main_parser.parse_args(["--help"])

    files = []
    query = None
    recursive = False
    number_of_result = 1
    force = False
    chunk_size = -1
    overlap_ratio = 0.2
    query_multiplier = -1
    query_exclude = []
    check_item = None
    absolute = False
    match main_args.action:
        case "vectorise":
            files = main_args.file_paths
            recursive = main_args.recursive
            force = main_args.force
            chunk_size = main_args.chunk_size
            overlap_ratio = main_args.overlap
        case "query":
            query = main_args.query
            number_of_result = main_args.number
            query_multiplier = main_args.multiplier
            query_exclude = main_args.exclude
            absolute = main_args.absolute
        case "check":
            check_item = main_args.check_item
    return Config(
        action=CliAction(main_args.action),
        files=files,
        project_root=main_args.project_root,
        query=query,
        recursive=recursive,
        n_result=number_of_result,
        pipe=main_args.pipe,
        force=force,
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
        query_multiplier=query_multiplier,
        query_exclude=query_exclude,
        check_item=check_item,
        use_absolute_path=absolute,
    )


def expand_envs_in_dict(d: dict):
    if not isinstance(d, dict):
        return
    stack = [d]
    while stack:
        curr = stack.pop()
        for k in curr.keys():
            if isinstance(curr[k], str):
                curr[k] = os.path.expandvars(curr[k])
            elif isinstance(curr[k], dict):
                stack.append(curr[k])


async def load_config_file(path: Optional[PathLike] = None):
    """Load config file from ~/.config/vectorcode/config.json"""
    if path is None:
        path = GLOBAL_CONFIG_PATH
    if os.path.isfile(path):
        with open(path) as fin:
            config = json.load(fin)
        expand_envs_in_dict(config)
        return await Config.import_from(config)
    return Config()


async def find_project_config_dir(start_from: PathLike = "."):
    """Returns the project-local config directory."""
    current_dir = Path(start_from).resolve()
    project_root_anchors = [".vectorcode", ".git"]
    while current_dir:
        for anchor in project_root_anchors:
            to_be_checked = os.path.join(current_dir, anchor)
            if os.path.isdir(to_be_checked):
                return to_be_checked
        parent = current_dir.parent
        if parent.resolve() == current_dir:
            return
        current_dir = parent.resolve()


def expand_path(path: PathLike, absolute: bool = False) -> PathLike:
    expanded = os.path.expanduser(os.path.expandvars(path))
    if absolute:
        return os.path.abspath(expanded)
    return expanded


async def expand_globs(
    paths: list[PathLike], recursive: bool = False
) -> list[PathLike]:
    result = set()
    stack = paths
    while stack:
        curr = stack.pop()
        if os.path.isfile(curr):
            result.add(expand_path(curr))
        elif "*" in str(curr):
            stack.extend(glob.glob(str(curr), recursive=recursive))
        elif os.path.isdir(curr) and recursive:
            stack.extend(glob.glob(os.path.join(curr, "**", "*"), recursive=recursive))
    return list(result)
