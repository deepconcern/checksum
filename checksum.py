from argparse import ArgumentParser
from hashlib import md5
from humanize import naturalsize
from io import DEFAULT_BUFFER_SIZE
from pathlib import Path
from progress.bar import Bar
from sys import exit
from typing import Callable, NoReturn, TypeAlias, Union

ReadOnlyBuffer = bytes
WriteableBuffer = Union[bytearray, memoryview]
ReadableBuffer = Union[ReadOnlyBuffer, WriteableBuffer]

NextProgress: TypeAlias = Callable[[], None]
UpdateHash: TypeAlias = Callable[[ReadableBuffer], None]

def main(path_str: str, is_recursive: bool, is_verbose: bool) -> None:
    class HashingBar(Bar):
        message = 'Hashing %(max_human)s'
        suffix = '%(percent).1f%%'

        @property
        def max_human(self):
            return naturalsize(self.max, binary=True)

    def error(message: str) -> NoReturn:
        exit(f"{Path(__file__).name}: error: {message}")

    def file_size(path: Path) -> int:
        if is_verbose:
            print(f"Calculating size: {str(path)}")

        return path.stat().st_size

    def dir_size(path: Path) -> int:
        if is_verbose:
            print(f"Calculating size: {str(path)}")

        size = 0

        for child in path.iterdir():
            if child.is_dir():
                size += dir_size(child)
            else:
                size += file_size(child)

        return size

    def file_hash(update_hash: UpdateHash, path: Path, next_progress: NextProgress) -> None:
        with open(path, 'rb') as file:
            while chunk := file.read(DEFAULT_BUFFER_SIZE * 4):
                update_hash(chunk)
                next_progress(len(chunk))

    def dir_hash(update_hash: UpdateHash, path: Path, next_progress: NextProgress) -> None:
        for child in path.iterdir():
            if child.is_dir():
                dir_hash(update_hash, child, next_progress)
            else:
                file_hash(update_hash, child, next_progress)

    p = Path(path_str)
    
    hash = md5()

    if is_recursive:
        num_bytes = dir_size(p)

        print(f"Bytes to hash: {num_bytes}")

        with HashingBar(max=num_bytes) as bar:
            dir_hash(hash.update, p , bar.next)
    else:
        if p.is_dir():
            error('directory found but "--recursive" is not set')

        num_bytes = file_size(p)

        print(f"Bytes to hash: {num_bytes}")

        with HashingBar(max=num_bytes) as bar:
            file_hash(hash.update, p , bar.next)

    print(f"Hash: {hash.hexdigest()}")

if __name__ == '__main__':
    arg_parser = ArgumentParser()

    arg_parser.add_argument('path',
        help='The path of the file/folder to provide a checksum for')
        
    arg_parser.add_argument('-r', '--recursive',
        help='If set, does a checksum recursively through all child files and folders',
        action='store_true')
    arg_parser.add_argument('-v', '--verbose',
        help='If set, prints extra information',
        action='store_true')

    args = arg_parser.parse_args()

    main(args.path, args.recursive, args.verbose)