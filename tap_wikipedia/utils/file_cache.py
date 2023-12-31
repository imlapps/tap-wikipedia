import json
import logging
import mimetypes

import os
import gzip
from pathlib import Path
from ssl import SSLContext
from time import sleep
from typing import Optional, Dict, Any
from urllib.request import urlopen

from pathvalidate import sanitize_filename


class FileCache:
    def __init__(
        self,
        *,
        # atomic_download: bool = False,
        cache_dir_path: Path,
        sleep_s_after_download: Optional[float] = None,
        ssl_context: Optional[SSLContext] = None,
    ):
        """
        :param cache_dir_path: directory where files from URLs can be cached
        """
        # self.__atomic_download = atomic_download
        self.__cache_dir_path = cache_dir_path
        self.__cache_dir_path.mkdir(exist_ok=True, parents=True)
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__sleep_s_after_download = sleep_s_after_download
        self.__ssl_context = ssl_context

    def __cached_file_extension(
        self, *, file_url: str, file_mime_type: Optional[str]
    ) -> str:
        if file_mime_type is not None:
            cached_file_extension = mimetypes.guess_extension(
                file_mime_type, strict=False
            )

            if cached_file_extension is not None:
                self.__logger.debug(
                    "guessed file extension %s from Content-Type %s",
                    cached_file_extension,
                    file_mime_type,
                )
                return cached_file_extension

        guessed_mime_type, _ = mimetypes.guess_type(file_url, strict=False)
        if guessed_mime_type is not None:
            self.__logger.debug(
                "guessed MIME type %s from file URL %s",
                guessed_mime_type,
                file_url,  # noqa: E501
            )
            cached_file_extension = mimetypes.guess_extension(
                guessed_mime_type, strict=False
            )
            if cached_file_extension is not None:
                self.__logger.debug(
                    "guessed file extension %s from guessed MIME type %s",
                    cached_file_extension,
                    guessed_mime_type,
                )
                return cached_file_extension

        raise ValueError(f"unable to guess file extension for {file_url}")

    def __file_cache_dir_path(self, *, file_url: str) -> Path:
        return self.__cache_dir_path / sanitize_filename(str(file_url))

    def get_file(
        self,
        file_url: str,
        *,
        file_extension: Optional[str] = None,
        force_download=False,
    ) -> Path:
        """
        Get file from the cache, downloading if necessary.
        :return path to the file in the cache directory
        """

        # Store each file in a different directory,
        # alongside its metadata. The file will be:
        # <root dir path>/<sanitized version of file URL>/file.<extension>
        # The headers will be in the same directory as headers.txt.

        assert not str(file_url).startswith("file:")

        file_cache_dir_path = self.__file_cache_dir_path(file_url=file_url)

        if not force_download and file_cache_dir_path.is_dir():
            for file_name in os.listdir(file_cache_dir_path):
                cached_file_path = file_cache_dir_path / file_name
                if not cached_file_path.is_file():
                    continue
                file_base_name = os.path.splitext(file_name)[0]
                if file_base_name == "abstracts":
                    # Cache hit
                    self.__logger.debug(
                        "cached file %s exists for URL %s and force_download not specified, using cached data",  # noqa: E501
                        cached_file_path,
                        file_url,
                    )
                    return cached_file_path

        def get_cached_file_path(headers_dict: Dict[str, Any]) -> Path:
            if file_extension is not None:
                return file_cache_dir_path / (
                    "abstracts"
                    + ("." if not file_extension.startswith(".") else "")
                    + file_extension
                )

            headers_dict_lower = {
                key.lower(): value for key, value in headers_dict.items()
            }
            content_type_header_value = headers_dict_lower.get("content-type")
            if content_type_header_value:
                file_mime_type = content_type_header_value.split(";", 1)[0]
            else:
                file_mime_type = None
            cached_file_extension = self.__cached_file_extension(
                file_mime_type=file_mime_type, file_url=file_url
            )
            return file_cache_dir_path / ("abstracts" + cached_file_extension)

        # Force download or cache miss
        self.__logger.debug("downloading %s", file_url)
        with urlopen(
            str(file_url), context=self.__ssl_context
        ) as open_file_url:  # noqa: E501
            open_file_headers_dict = {
                key: value for key, value in open_file_url.headers.items()
            }
            cached_file_path = get_cached_file_path(open_file_headers_dict)
            cached_file_path.unlink(missing_ok=True)
            file_cache_dir_path.mkdir(exist_ok=True, parents=True)

            with gzip.GzipFile(fileobj=open_file_url) as uncompressed_file:
                file_content = uncompressed_file.read()

            with open(cached_file_path, "wb") as cached_file:
                cached_file.write(file_content)
                self.__logger.debug(
                    "downloaded %s to %s", file_url, cached_file_path
                )  # noqa: E501

        headers_json_file_path = file_cache_dir_path / "headers.json"
        with open(
            headers_json_file_path, "w+", encoding="utf-8"
        ) as headers_json_file:  # noqa: E501
            json.dump(open_file_headers_dict, headers_json_file)
            self.__logger.debug(
                "wrote %s headers to %s", file_url, headers_json_file_path
            )

        if self.__sleep_s_after_download is not None:
            self.__logger.debug(
                "sleeping %.2f seconds after downloading %s",
                self.__sleep_s_after_download,
                file_url,
            )
            sleep(self.__sleep_s_after_download)

        return cached_file_path

    def put_file(
        self,
        *,
        file_data: bytes,
        file_url: str,
        file_mime_type: Optional[str] = None,
        file_extension: Optional[str] = None,
    ) -> Path:
        file_cache_dir_path = self.__file_cache_dir_path(file_url=file_url)
        if file_extension is None:
            file_extension = self.__cached_file_extension(
                file_mime_type=file_mime_type, file_url=file_url
            )
        cached_file_path = file_cache_dir_path / ("file" + file_extension)
        file_cache_dir_path.mkdir(exist_ok=True)
        with open(cached_file_path, "w+b") as cached_file:
            cached_file.write(file_data)
        return cached_file_path
