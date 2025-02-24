import os
import socket
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

import httpx
import pytest
from chromadb.api import AsyncClientAPI
from chromadb.config import Settings

from vectorcode.cli_utils import Config
from vectorcode.common import (
    get_client,
    get_collection,
    get_collection_name,
    get_embedding_function,
    start_server,
    try_server,
    verify_ef,
    wait_for_server,
)


def test_get_collection_name():
    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        file_path = os.path.join(temp_dir, "test_file.txt")
        collection_name = get_collection_name(file_path)
        assert isinstance(collection_name, str)
        assert len(collection_name) == 63

        # Test that the collection name is consistent for the same path
        collection_name2 = get_collection_name(file_path)
        assert collection_name == collection_name2

        # Test that the collection name is different for different paths
        file_path2 = os.path.join(temp_dir, "another_file.txt")
        collection_name2 = get_collection_name(file_path2)
        assert collection_name != collection_name2

        # Test with absolute path
        abs_file_path = os.path.abspath(file_path)
        collection_name3 = get_collection_name(abs_file_path)
        assert collection_name == collection_name3


def test_get_embedding_function():
    # Test with a valid embedding function
    config = Config(
        embedding_function="SentenceTransformerEmbeddingFunction", embedding_params={}
    )
    embedding_function = get_embedding_function(config)
    assert "SentenceTransformerEmbeddingFunction" in str(type(embedding_function))

    # Test with an invalid embedding function (fallback to SentenceTransformer)
    config = Config(embedding_function="FakeEmbeddingFunction", embedding_params={})
    embedding_function = get_embedding_function(config)
    assert "SentenceTransformerEmbeddingFunction" in str(type(embedding_function))

    # Test with specific embedding parameters
    config = Config(
        embedding_function="SentenceTransformerEmbeddingFunction",
        embedding_params={"param1": "value1"},
    )
    embedding_function = get_embedding_function(config)
    assert "SentenceTransformerEmbeddingFunction" in str(type(embedding_function))


@pytest.mark.asyncio
async def test_try_server():
    # This test requires a server to be running, so it's difficult to make it truly isolated.
    # For now, let's just check that it returns False when the server is not running on a common port.
    assert not await try_server("localhost", 9999)


@pytest.mark.asyncio
async def test_wait_for_server_timeout():
    with pytest.raises(TimeoutError):
        await wait_for_server("localhost", 9999, timeout=1)


@pytest.mark.asyncio
async def test_get_client():
    # Patch chromadb.AsyncHttpClient to avoid actual network calls
    with patch("chromadb.AsyncHttpClient") as MockAsyncHttpClient:
        mock_client = MagicMock(spec=AsyncClientAPI)
        MockAsyncHttpClient.return_value = mock_client

        config = Config(host="test_host", port=1234, db_path="test_db")
        client = await get_client(config)

        assert isinstance(client, AsyncClientAPI)
        MockAsyncHttpClient.assert_called_once_with(
            host="test_host", port=1234, settings=Settings(anonymized_telemetry=False)
        )

        # Test with valid db_settings (only anonymized_telemetry)
        config = Config(
            host="test_host",
            port=1234,
            db_path="test_db",
            db_settings={"anonymized_telemetry": True},
        )
        client = await get_client(config)

        assert isinstance(client, AsyncClientAPI)
        MockAsyncHttpClient.assert_called_with(
            host="test_host", port=1234, settings=Settings(anonymized_telemetry=True)
        )

        # Test with multiple db_settings, including an invalid one.  The invalid one
        # should be filtered out inside get_client.
        config = Config(
            host="test_host",
            port=1234,
            db_path="test_db",
            db_settings={"anonymized_telemetry": True, "other_setting": "value"},
        )
        client = await get_client(config)
        assert isinstance(client, AsyncClientAPI)
        MockAsyncHttpClient.assert_called_with(
            host="test_host",
            port=1234,
            settings=Settings(anonymized_telemetry=True),
        )


def test_verify_ef():
    # Mocking AsyncCollection and Config
    mock_collection = MagicMock()
    mock_config = MagicMock()

    # Test when collection_ef and config.embedding_function are the same
    mock_collection.metadata = {"embedding_function": "test_embedding_function"}
    mock_config.embedding_function = "test_embedding_function"
    assert verify_ef(mock_collection, mock_config) is True

    # Test when collection_ef and config.embedding_function are different
    mock_collection.metadata = {"embedding_function": "test_embedding_function"}
    mock_config.embedding_function = "another_embedding_function"
    assert verify_ef(mock_collection, mock_config) is False

    # Test when collection_ep and config.embedding_params are the same
    mock_collection.metadata = {"embedding_params": {"param1": "value1"}}
    mock_config.embedding_params = {"param1": "value1"}
    assert verify_ef(mock_collection, mock_config) is True

    # Test when collection_ep and config.embedding_params are different
    mock_collection.metadata = {"embedding_params": {"param1": "value1"}}
    mock_config.embedding_params = {"param1": "value2"}
    assert (
        verify_ef(mock_collection, mock_config) is True
    )  # It should return True according to the source code.

    # Test when collection_ef is None
    mock_collection.metadata = {}
    mock_config.embedding_function = "test_embedding_function"
    assert verify_ef(mock_collection, mock_config) is True


@patch("socket.socket")
@pytest.mark.asyncio
async def test_try_server_mocked(mock_socket):
    # Mocking httpx.AsyncClient and its get method to simulate a successful connection
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )
        assert await try_server("localhost", 8000) is True

    # Mocking httpx.AsyncClient to raise a ConnectError
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = (
            httpx.ConnectError("Simulated connection error")
        )
        assert await try_server("localhost", 8000) is False

    # Mocking httpx.AsyncClient to raise a ConnectTimeout
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = (
            httpx.ConnectTimeout("Simulated connection timeout")
        )
        assert await try_server("localhost", 8000) is False


@pytest.mark.asyncio
async def test_get_collection():
    config = Config(
        host="test_host",
        port=1234,
        db_path="test_db",
        embedding_function="SentenceTransformerEmbeddingFunction",
        embedding_params={},
        project_root="/test_project",
    )

    # Test retrieving an existing collection
    with patch("chromadb.AsyncHttpClient") as MockAsyncHttpClient:
        mock_client = MagicMock(spec=AsyncClientAPI)
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        MockAsyncHttpClient.return_value = mock_client

        collection = await get_collection(mock_client, config)
        assert collection == mock_collection
        mock_client.get_collection.assert_called_once()
        mock_client.get_or_create_collection.assert_not_called()

    # Test creating a collection if it doesn't exist
    with patch("chromadb.AsyncHttpClient") as MockAsyncHttpClient:
        mock_client = MagicMock(spec=AsyncClientAPI)
        mock_collection = MagicMock()
        mock_collection.metadata = {
            "hostname": socket.gethostname(),
            "username": os.environ.get(
                "USER", os.environ.get("USERNAME", "DEFAULT_USER")
            ),
            "created-by": "VectorCode",
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        MockAsyncHttpClient.return_value = mock_client

        collection = await get_collection(mock_client, config, make_if_missing=True)
        assert collection == mock_collection
        mock_client.get_or_create_collection.assert_called_once()

    # Test raising ValueError if collection doesn't exist and make_if_missing is False
    with patch("chromadb.AsyncHttpClient") as MockAsyncHttpClient:
        mock_client = MagicMock(spec=AsyncClientAPI)
        mock_client.get_collection.side_effect = ValueError("Collection not found")
        MockAsyncHttpClient.return_value = mock_client
        with pytest.raises(ValueError):
            await get_collection(mock_client, config, make_if_missing=False)

    # Test raising IndexError on hash collision.
    with patch("chromadb.AsyncHttpClient") as MockAsyncHttpClient:
        mock_client = MagicMock(spec=AsyncClientAPI)
        mock_client.get_or_create_collection.side_effect = IndexError(
            "Hash collision occurred"
        )
        MockAsyncHttpClient.return_value = mock_client
        with pytest.raises(IndexError):
            await get_collection(mock_client, config, make_if_missing=True)


@pytest.mark.asyncio
async def test_start_server():
    # Mock subprocess.Popen
    with (
        patch("asyncio.create_subprocess_exec") as MockCreateProcess,
        patch("asyncio.sleep"),
        patch("socket.socket") as MockSocket,
        patch("vectorcode.common.wait_for_server") as MockWaitForServer,
    ):
        # Mock socket to return a specific port
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ("localhost", 12345)  # Mock port
        MockSocket.return_value.__enter__.return_value = mock_socket

        # Mock the process object
        mock_process = MagicMock()
        mock_process.returncode = 0  # Simulate successful execution
        MockCreateProcess.return_value = mock_process

        # Create a config object
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                host="localhost",
                port=8000,
                db_path=temp_dir,
                project_root=temp_dir,
            )

            # Call start_server
            process = await start_server(config)

            # Assert that asyncio.create_subprocess_exec was called with the correct arguments
            MockCreateProcess.assert_called_once()
            args, kwargs = MockCreateProcess.call_args
            expected_args = [
                sys.executable,
                "-m",
                "chromadb.cli.cli",
                "run",
                "--host",
                "localhost",
                "--port",
                str(12345),  # Check the mocked port
                "--path",
                temp_dir,
                "--log-path",
                os.path.join(temp_dir, "chroma.log"),
            ]
            assert args[0] == sys.executable
            assert tuple(args[1:]) == tuple(expected_args[1:])
            assert kwargs["stdout"] == subprocess.DEVNULL
            assert kwargs["stderr"] == sys.stderr
            assert "ANONYMIZED_TELEMETRY" in kwargs["env"]

            # Assert that wait_for_server was called with the correct arguments
            MockWaitForServer.assert_called_once_with("localhost", 12345)

            # Assert that the function returns the process
            assert process == mock_process
