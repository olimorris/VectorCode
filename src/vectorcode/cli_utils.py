import argparse
from dataclasses import dataclass, fields, field
from enum import Enum
import glob
import os
from pathlib import Path
from typing import Any, Optional, Union
import json

PathLike = Union[str, Path]


class CliAction(Enum):
    vectorise = "vectorise"
    query = "query"
    drop = "drop"
    ls = "ls"


@dataclass
class Config:
    recursive: bool = False
    to_be_deleted: list[str] = field(default_factory=list)
    pipe: bool = False
    action: Optional[CliAction] = None
    files: list[PathLike] = field(default_factory=list)
    project_root: PathLike = Path(".")
    query: Optional[str] = None
    host: str = "localhost"
    port: int = 8000
    embedding_function: str = "DefaultEmbeddingFunction"
    embedding_params: dict[str, Any] = field(default_factory=(lambda: {}))
    n_result: int = 3

    @classmethod
    def import_from(cls, config_dict: dict[str, Any]) -> "Config":
        ef = config_dict.get("embedding_function")
        if not isinstance(ef, str):
            ef = "DefaultEmbeddingFunction"
        ep = config_dict.get("embedding_params")
        if not isinstance(ep, dict):
            ep = {}
        host = config_dict.get("host")
        if not isinstance(host, str):
            host = "localhost"
        port = config_dict.get("port")
        if not isinstance(port, int):
            port = 8000
        return Config(
            **{
                "embedding_function": ef,
                "embedding_params": ep,
                "host": host,
                "port": port,
            }
        )

    def merge_from(self, other: "Config") -> "Config":
        final_config = {}
        default_config = Config()
        for merged_field in fields(self):
            final_config[merged_field.name] = getattr(other, merged_field.name)
            if not final_config[merged_field.name] or final_config[
                merged_field.name
            ] == getattr(default_config, merged_field.name):
                final_config[merged_field.name] = getattr(self, merged_field.name)
        return Config(**final_config)


def cli_arg_parser():
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument(
        "--project_root",
        default="",
        help="Project root to be used as an identifier of the project.",
    )
    shared_parser.add_argument(
        "--pipe",
        "-p",
        action="store_true",
        default=False,
        help="Print structured output for other programs to process.",
    )
    main_parser = argparse.ArgumentParser("vectorcode", parents=[shared_parser])

    subparsers = main_parser.add_subparsers(dest="action", required=False)
    subparsers.add_parser("ls", parents=[shared_parser], help="List all collections.")

    vectorise_parser = subparsers.add_parser(
        "vectorise",
        parents=[shared_parser],
        help="Vectorise and send documents to chromadb.",
    )
    vectorise_parser.add_argument(
        "file_paths", nargs="+", help="Paths to files to be vectorised."
    )
    vectorise_parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=False,
        help="Recursive indexing for directories.",
    )

    query_parser = subparsers.add_parser(
        "query", parents=[shared_parser], help="Send query to retrieve documents."
    )
    query_parser.add_argument("query", nargs="+", help="Query keywords.")
    query_parser.add_argument(
        "-n", "--number", type=int, default=1, help="Number of results to retrieve."
    )

    subparsers.add_parser("drop", parents=[shared_parser], help="Remove a collection.")

    shared_args, unknowns = shared_parser.parse_known_args()
    main_args = main_parser.parse_args(unknowns)
    if main_args.action is None:
        main_args = main_parser.parse_args(["--help"])

    files = []
    query = None
    recursive = False
    number_of_result = 1
    if main_args.action == "vectorise":
        files = main_args.file_paths
        recursive = main_args.recursive
    elif main_args.action == "query":
        query = " ".join(main_args.query)
        number_of_result = main_args.number
    return Config(
        action=CliAction(main_args.action),
        files=files,
        project_root=main_args.project_root or shared_args.project_root,
        query=query,
        recursive=recursive,
        n_result=number_of_result,
        pipe=main_args.pipe or shared_args.pipe,
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


def load_config_file():
    """Load config file from ~/.config/vectorcode/config.json"""
    config_path = os.path.join(
        os.path.expanduser("~"), ".config", "vectorcode", "config.json"
    )
    if os.path.isfile(config_path):
        with open(config_path) as fin:
            config = json.load(fin)
        expand_envs_in_dict(config)
        return Config.import_from(config)
    return Config()


def expand_path(path: PathLike, absolute: bool = False) -> PathLike:
    expanded = os.path.expanduser(os.path.expandvars(path))
    if absolute:
        return os.path.abspath(expanded)
    return expanded


def expand_globs(paths: list[PathLike], recursive: bool = False) -> list[PathLike]:
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
