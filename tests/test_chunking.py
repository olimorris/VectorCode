from vectorcode.chunking import FileChunker, StringChunker


class TestChunking:
    file_chunker = FileChunker()

    def test_string_chunker(self):
        string_chunker = StringChunker(chunk_size=5, overlap_ratio=0.5)
        assert list(string_chunker.chunk("hello world")) == [
            "hello",
            "llo w",
            "o wor",
            "world",
        ]
        string_chunker = StringChunker(chunk_size=5, overlap_ratio=0)
        assert list(string_chunker.chunk("hello world")) == ["hello", " worl", "d"]

        string_chunker = StringChunker(chunk_size=5, overlap_ratio=0.8)
        assert list(string_chunker.chunk("hello world")) == [
            "hello",
            "ello ",
            "llo w",
            "lo wo",
            "o wor",
            " worl",
            "world",
        ]

    def test_file_chunker(self):
        """
        Use StringChunker output as ground truth to test chunking.
        """
        file_path = __file__
        ratio = 0.5
        chunk_size = 100
        with open(file_path) as fin:
            string_chunker = StringChunker(chunk_size=chunk_size, overlap_ratio=ratio)
            string_chunks = list(string_chunker.chunk(fin.read()))

        with open(file_path) as fin:
            file_chunker = FileChunker(chunk_size=chunk_size, overlap_ratio=ratio)
            file_chunks = list(file_chunker.chunk(fin))

        assert len(string_chunks) == len(file_chunks), (
            f"Number of chunks do not match. {len(string_chunks)} != {len(file_chunks)}"
        )
        for string_chunk, file_chunk in zip(string_chunks, file_chunks):
            assert string_chunk == file_chunk
