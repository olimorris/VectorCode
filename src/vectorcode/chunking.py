from abc import abstractmethod
from io import TextIOWrapper
from typing import Generator


class ChunkerBase:
    def __init__(self) -> None:
        pass

    @abstractmethod
    def chunk(self, data) -> Generator[str, None, None]:
        raise NotImplementedError


class StringChunker(ChunkerBase):
    def __init__(self, chunk_size: int = -1, overlap_ratio: float = 0.2) -> None:
        super().__init__()
        self.__chunk_size = chunk_size
        assert 0 <= overlap_ratio < 1, (
            "Overlap ratio has to be a float between 0 (inclusive) and 1 (exclusive)."
        )
        self.__overlap_ratio = overlap_ratio

    def chunk(self, data: str) -> Generator[str, None, None]:
        if self.__chunk_size < 0:
            yield data
        else:
            step_size = max(1, int(self.__chunk_size * (1 - self.__overlap_ratio)))
            i = 0
            while i < len(data):
                yield data[i : i + self.__chunk_size]
                if i + self.__chunk_size >= len(data):
                    break
                i += step_size


class FileChunker(ChunkerBase):
    def __init__(self, chunk_size: int = -1, overlap_ratio: float = 0.2) -> None:
        super().__init__()
        self.__chunk_size = chunk_size
        assert 0 <= overlap_ratio < 1, (
            "Overlap ratio has to be a float between 0 (inclusive) and 1 (exclusive)."
        )
        self.__overlap_ratio = overlap_ratio

    def chunk(self, data: TextIOWrapper) -> Generator[str, None, None]:
        if self.__chunk_size < 0:
            yield "".join(data.readlines())
        else:
            step_size = max(1, int(self.__chunk_size * (1 - self.__overlap_ratio)))
            # the output of this method should be identical to that of StringChunker.chunk
            output = data.read(self.__chunk_size)
            yield output
            if len(output) < self.__chunk_size:
                return
            while True:
                new_chars = data.read(step_size)
                output = output[step_size:] + new_chars
                yield output
                if len(new_chars) < step_size:
                    return
