#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PyFreeFEM パッケージ

FreeFEMとPython間の共有メモリ通信（Linux）またはファイルIO（Windows、macOS）を
実現するためのツールを提供します。
"""

__version__ = "0.1.0"
__author__ = "PyFreeFEM開発チーム"

import platform
import os

# ファイルIO通信用モジュール
from .file_io import FreeFEMFileIO

# エラー定義
from .errors import (
    FreeFEMBaseError,
    FreeFEMExecutionError,
    DataTransferError,
    TimeoutError,
    FileOperationError
)

# データ変換
from .data_converter import convert_to_freefem, convert_from_freefem

# Linux環境の場合のみ共有メモリモジュールをインポート
if platform.system() == 'Linux':
    # 共有メモリ通信用コアモジュール
    from .shm_manager import SharedMemoryManager
    from .freefem_interface import FreeFEMInterface
    from .freefem_runner import FreeFEMRunner
    
    # Linuxのみのシンボルをパッケージとしてエクスポート
    __linux_symbols__ = [
        "SharedMemoryManager", 
        "FreeFEMInterface",
        "FreeFEMRunner",
    ]
else:
    # Windows/macOSで未定義のシンボルを空にする
    __linux_symbols__ = []

# パッケージとして公開するシンボル
__all__ = [
    "FreeFEMFileIO",
    "convert_to_freefem",
    "convert_from_freefem",
    "FreeFEMBaseError",
    "FreeFEMExecutionError",
    "DataTransferError",
    "TimeoutError",
    "FileOperationError",
    "PyFreeFEM"  # 統一インターフェース
] + __linux_symbols__

# 統一インターフェースクラス
class PyFreeFEM:
    """
    FreeFEMとの統一インターフェース
    
    OSに応じて適切な実装（共有メモリまたはファイルIO）を選択します。
    Linux: 共有メモリ通信（FreeFEMRunner）
    Windows/macOS: ファイルIO通信（FreeFEMFileIO）
    """
    
    def __init__(self, freefem_path=None, debug=False, wsl_mode=False, **kwargs):
        """
        初期化
        
        Args:
            freefem_path (str): FreeFEM実行ファイルのパス
            debug (bool): デバッグモードを有効にするかどうか
            wsl_mode (bool): WSL環境での実行モード（Windowsのみ有効）
            **kwargs: その他の実装固有の引数
        """
        self.system = platform.system()
        self.debug = debug
        self.wsl_mode = wsl_mode
        
        if freefem_path is None:
            # デフォルトのFreeFEMパス
            if self.system == 'Windows' and wsl_mode:
                freefem_path = ['wsl', '-d', 'Ubuntu', '-e', 'FreeFem++']
            else:
                freefem_path = 'FreeFem++'
        
        # OSに応じた実装を選択
        if self.system == 'Linux':
            self.implementation = 'shm'
            self.runner = FreeFEMRunner(
                freefem_path=freefem_path,
                debug=debug,
                **kwargs
            )
        else:
            self.implementation = 'file_io'
            working_dir = kwargs.get('working_dir', None)
            self.runner = FreeFEMFileIO(
                freefem_path=freefem_path,
                working_dir=working_dir,
                debug=debug
            )
        
        if debug:
            print(f"PyFreeFEM初期化: システム={self.system}, 実装={self.implementation}")
    
    def start_session(self):
        """セッションを開始"""
        if self.implementation == 'shm' and hasattr(self.runner, 'start_session'):
            return self.runner.start_session()
        return True
    
    def end_session(self):
        """セッションを終了"""
        if self.implementation == 'shm' and hasattr(self.runner, 'end_session'):
            return self.runner.end_session()
        return True
    
    def run_script(self, script_path, input_data=None, **kwargs):
        """
        FreeFEMスクリプトを実行
        
        Args:
            script_path (str): 実行するFreeFEMスクリプトのパス
            input_data (np.ndarray, optional): 入力データ（ファイルIO使用時）
            **kwargs: その他の実装固有の引数
            
        Returns:
            実装に応じた戻り値:
            - 共有メモリ: (成功フラグ, 標準出力, 標準エラー出力)
            - ファイルIO: (成功フラグ, 出力データ, 標準出力, 標準エラー出力)
        """
        if self.implementation == 'shm':
            return self.runner.run_script(script_path, **kwargs)
        else:
            return self.runner.run_script(script_path, input_data=input_data, **kwargs)
    
    def run_inline_script(self, script_content, input_data=None, **kwargs):
        """
        インラインFreeFEMスクリプトを実行
        
        Args:
            script_content (str): 実行するFreeFEMスクリプトの内容
            input_data (np.ndarray, optional): 入力データ（ファイルIO使用時）
            **kwargs: その他の実装固有の引数
            
        Returns:
            実装に応じた戻り値
        """
        if self.implementation == 'shm' and hasattr(self.runner, 'run_inline_script'):
            return self.runner.run_inline_script(script_content, **kwargs)
        else:
            # ファイルIOの場合は一時ファイルを作成
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.edp', delete=False) as f:
                f.write(script_content.encode('utf-8'))
                temp_path = f.name
            
            try:
                result = self.runner.run_script(temp_path, input_data=input_data, **kwargs)
                return result
            finally:
                # 一時ファイルを削除
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    # 実装に依存するメソッドの転送
    def __getattr__(self, name):
        """実装固有のメソッドを転送"""
        if hasattr(self.runner, name):
            return getattr(self.runner, name)
        raise AttributeError(f"'{self.__class__.__name__}' オブジェクトは '{name}' 属性を持っていません") 