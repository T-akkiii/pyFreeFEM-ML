#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PyFreeFEM パッケージ

FreeFEMとPython間の共有メモリ通信を実現するためのツールを提供します。
"""

__version__ = "0.1.0"
__author__ = "PyFreeFEM開発チーム"

# 共有メモリ通信用コアモジュール
from .shm_manager import SharedMemoryManager
from .freefem_interface import FreeFEMInterface
from .freefem_runner import FreeFEMRunner
from .data_converter import convert_to_freefem, convert_from_freefem
from .errors import (
    FreeFEMBaseError,
    FreeFEMExecutionError,
    DataTransferError,
    TimeoutError,
    FileOperationError
)

# パッケージとして公開するシンボル
__all__ = [
    "SharedMemoryManager", 
    "FreeFEMInterface",
    "FreeFEMRunner",
    "convert_to_freefem",
    "convert_from_freefem",
    "FreeFEMBaseError",
    "FreeFEMExecutionError",
    "DataTransferError",
    "TimeoutError",
    "FileOperationError"
] 