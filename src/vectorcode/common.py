import hashlib
import os
import socket
import sys
from typing import Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.utils import embedding_functions

from vectorcode.cli_utils import Config, expand_path
import httpx


def get_client(configs: Config) -> ClientAPI:
    try:
        client = chromadb.HttpClient(host=configs.host, port=configs.port)
        return client
    except ValueError:
        print(
            f"Failed to access the chromadb server at {configs.host}:{configs.port}. Please verify your setup and configurations."
        )
        sys.exit(1)


def get_collection_name(full_path: str) -> str:
    full_path = str(expand_path(full_path, absolute=True))
    hasher = hashlib.sha256()
    hasher.update(f"{os.environ['USER']}@{socket.gethostname()}:{full_path}".encode())
    collection_id = hasher.hexdigest()[:63]
    return collection_id


def get_embedding_function(configs: Config) -> Optional[chromadb.EmbeddingFunction]:
    try:
        return getattr(embedding_functions, configs.embedding_function)(
            **configs.embedding_params
        )
    except AttributeError:
        print(
            f"Failed to use {configs.embedding_function}. Falling back to Sentence Transformer."
        )
        return embedding_functions.DefaultEmbeddingFunction()


def make_or_get_collection(client: ClientAPI, configs: Config):
    full_path = str(expand_path(configs.project_root, absolute=True))
    collection = client.get_or_create_collection(
        get_collection_name(full_path),
        metadata={
            "path": full_path,
            "hostname": socket.gethostname(),
            "created-by": "VectorCode",
            "username": os.environ["USER"],
            "embedding_function": configs.embedding_function,
        },
        embedding_function=get_embedding_function(configs),
    )
    if (
        not collection.metadata.get("hostname") == socket.gethostname()
        or not collection.metadata.get("username") == os.environ["USER"]
        or not collection.metadata.get("created-by") == "VectorCode"
    ):
        raise IndexError(
            "Failed to create the collection due to hash collision. Please file a bug report."
        )
    return collection
