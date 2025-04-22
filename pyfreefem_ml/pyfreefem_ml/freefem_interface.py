#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreeFEMインターフェースモジュール

このモジュールはPythonからFreeFEMを実行し、共有メモリを介してデータの
送受信を行うためのラッパークラスを提供します。
"""

import os
import sys
import time
import subprocess
import tempfile
import numpy as np
from pathlib import Path
import uuid

from .shm_manager import SharedMemoryManager

class FreeFEMInterface:
    """
    FreeFEMとの通信を行うための高レベルインターフェース
    
    このクラスは共有メモリを使用してPythonとFreeFEMの間でデータをやり取りし、
    FreeFEMスクリプトの実行と結果の取得を容易にします。
    """
    
    def __init__(self, shm_size=1024*1024, wsl_mode=False, debug=False, freefem_path=None, lib_dir=None):
        """
        FreeFEMインターフェースを初期化
        
        Args:
            shm_size (int): 共有メモリのサイズ（バイト単位）
            wsl_mode (bool): WSL環境での実行モードを有効にするかどうか
            debug (bool): デバッグモードを有効にするかどうか
            freefem_path (str): FreeFEM実行ファイルのパス（デフォルト: 'FreeFem++'）
            lib_dir (str): FreeFEMライブラリディレクトリのパス
        """
        self.debug = debug
        self.wsl_mode = wsl_mode
        self.freefem_path = freefem_path or 'FreeFem++'
        
        # 共有メモリ名として一意のIDを生成
        self.shm_name = f"freefem_shm_{uuid.uuid4().hex[:8]}"
        self.shm_size = shm_size
        
        # ライブラリディレクトリの設定
        self.lib_dir = lib_dir
        if self.lib_dir is None:
            # デフォルトのライブラリパスを設定
            if os.path.isdir(os.path.join(os.path.dirname(__file__), '..', 'freefem', 'libs')):
                self.lib_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'freefem', 'libs'))
            else:
                # 実行環境内で探索
                possible_paths = [
                    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'freefem', 'libs')),
                    '/usr/local/lib/ff++/4.10/idp',
                    '/usr/share/freefem/idp'
                ]
                for path in possible_paths:
                    if os.path.isdir(path):
                        self.lib_dir = path
                        break
        
        if self.debug:
            print(f"初期化: SHM名={self.shm_name}, サイズ={self.shm_size}, ライブラリパス={self.lib_dir}")
        
        # 共有メモリマネージャの初期化
        self.shm_manager = SharedMemoryManager(self.shm_name, self.shm_size)
        
    def __del__(self):
        """デストラクタ - リソースのクリーンアップ"""
        try:
            self.cleanup()
        except:
            pass
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if hasattr(self, 'shm_manager'):
            self.shm_manager.cleanup()
    
    def _convert_path_to_wsl(self, path):
        """
        Windowsパスを、WSL上で使用可能なパスに変換
        
        Args:
            path (str): 変換するWindowsパス
            
        Returns:
            str: WSL互換パス
        """
        if not self.wsl_mode or path.startswith('/'):
            return path
            
        # Windowsのドライブ文字が含まれるパスをWSL形式に変換
        if ':' in path:
            drive, rest = path.split(':', 1)
            wsl_path = f"/mnt/{drive.lower()}{rest.replace('\\', '/')}"
            return wsl_path
        else:
            # すでに相対パスか、ドライブ文字がない場合はそのまま返す
            return path.replace('\\', '/')
    
    def _prepare_freefem_env(self):
        """
        FreeFEM実行のための環境変数を準備
        
        Returns:
            dict: 環境変数の辞書
        """
        env = os.environ.copy()
        
        # 共有メモリ情報を環境変数で渡す
        env['FF_SHM_NAME'] = self.shm_name
        env['FF_SHM_SIZE'] = str(self.shm_size)
        
        # ライブラリパスの設定
        if self.lib_dir:
            lib_path = self._convert_path_to_wsl(self.lib_dir)
            if 'FF_INCLUDEPATH' in env:
                env['FF_INCLUDEPATH'] += f":{lib_path}"
            else:
                env['FF_INCLUDEPATH'] = lib_path
        
        if self.debug:
            print(f"環境変数: FF_SHM_NAME={env['FF_SHM_NAME']}, FF_SHM_SIZE={env['FF_SHM_SIZE']}")
            if 'FF_INCLUDEPATH' in env:
                print(f"FF_INCLUDEPATH={env['FF_INCLUDEPATH']}")
        
        return env
    
    def run_script(self, script_path, timeout=None):
        """
        FreeFEMスクリプトファイルを実行
        
        Args:
            script_path (str): FreeFEMスクリプトのパス
            timeout (int, optional): 実行タイムアウト（秒）
            
        Returns:
            tuple: (成功フラグ, 標準出力, 標準エラー出力)
        """
        if not os.path.exists(script_path):
            return False, "", f"Error: Script file not found: {script_path}"
        
        # WSLモードの場合のパス変換
        if self.wsl_mode:
            script_path = self._convert_path_to_wsl(script_path)
        
        # 環境変数の準備
        env = self._prepare_freefem_env()
        
        # FreeFEMコマンドの構築
        cmd = [self.freefem_path, script_path]
        
        if self.wsl_mode:
            # WSLを使用してコマンドを実行
            cmd = ['wsl', '-d', 'Ubuntu', 'bash', '-c', f"cd $(dirname '{script_path}') && {self.freefem_path} $(basename '{script_path}')"]
        
        if self.debug:
            print(f"実行コマンド: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            success = process.returncode == 0
            if self.debug:
                print(f"実行結果: code={process.returncode}, 成功={success}")
                if stdout:
                    print(f"標準出力:\n{stdout}")
                if stderr:
                    print(f"標準エラー:\n{stderr}")
            
            return success, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            return False, "", f"Error: Execution timed out after {timeout} seconds"
        except Exception as e:
            return False, "", f"Error: {str(e)}"
    
    def run_inline_script(self, script_content, timeout=None):
        """
        インラインFreeFEMスクリプトを実行
        
        Args:
            script_content (str): 実行するFreeFEMスクリプト内容
            timeout (int, optional): 実行タイムアウト（秒）
            
        Returns:
            tuple: (成功フラグ, 標準出力, 標準エラー出力)
        """
        # 一時ファイルの作成
        try:
            fd, temp_path = tempfile.mkstemp(suffix='.edp')
            os.close(fd)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            if self.debug:
                print(f"一時スクリプトファイル作成: {temp_path}")
            
            # スクリプトを実行
            result = self.run_script(temp_path, timeout)
            
            return result
            
        except Exception as e:
            return False, "", f"Error: {str(e)}"
        finally:
            # 一時ファイルの削除
            try:
                os.unlink(temp_path)
                if self.debug:
                    print(f"一時スクリプトファイル削除: {temp_path}")
            except:
                pass
    
    # ==== データ書き込みメソッド ====
    
    def write_int(self, value, name):
        """
        整数値を共有メモリに書き込み
        
        Args:
            value (int): 書き込む整数値
            name (str): 変数名
        """
        self.shm_manager.write_int(value, name)
        if self.debug:
            print(f"整数書き込み: {name} = {value}")
    
    def write_double(self, value, name):
        """
        実数値を共有メモリに書き込み
        
        Args:
            value (float): 書き込む実数値
            name (str): 変数名
        """
        self.shm_manager.write_double(value, name)
        if self.debug:
            print(f"実数書き込み: {name} = {value}")
    
    def write_string(self, value, name):
        """
        文字列を共有メモリに書き込み
        
        Args:
            value (str): 書き込む文字列
            name (str): 変数名
        """
        self.shm_manager.write_string(value, name)
        if self.debug:
            print(f"文字列書き込み: {name} = '{value}'")
    
    def write_array(self, array, name):
        """
        NumPy配列を共有メモリに書き込み
        
        Args:
            array (numpy.ndarray): 書き込む配列
            name (str): 変数名
        """
        self.shm_manager.write_array(array, name)
        if self.debug:
            shape_str = 'x'.join(str(s) for s in array.shape)
            print(f"配列書き込み: {name}, 形状={shape_str}, 型={array.dtype}")
    
    # ==== データ読み取りメソッド ====
    
    def read_int(self, name):
        """
        共有メモリから整数値を読み取り
        
        Args:
            name (str): 変数名
            
        Returns:
            int: 読み取った整数値
        """
        value = self.shm_manager.read_int(name)
        if self.debug:
            print(f"整数読み取り: {name} = {value}")
        return value
    
    def read_double(self, name):
        """
        共有メモリから実数値を読み取り
        
        Args:
            name (str): 変数名
            
        Returns:
            float: 読み取った実数値
        """
        value = self.shm_manager.read_double(name)
        if self.debug:
            print(f"実数読み取り: {name} = {value}")
        return value
    
    def read_string(self, name):
        """
        共有メモリから文字列を読み取り
        
        Args:
            name (str): 変数名
            
        Returns:
            str: 読み取った文字列
        """
        value = self.shm_manager.read_string(name)
        if self.debug:
            print(f"文字列読み取り: {name} = '{value}'")
        return value
    
    def read_array(self, name, offset=0, shape=None, dtype=np.float64):
        """
        共有メモリからNumPy配列を読み取り
        
        Args:
            name (str): 変数名
            offset (int, optional): 配列データのオフセット位置
            shape (tuple, optional): 配列の形状、指定がない場合は検出を試みる
            dtype (numpy.dtype, optional): 配列のデータ型、デフォルトはnp.float64
            
        Returns:
            numpy.ndarray: 読み取った配列
        """
        array = self.shm_manager.read_array(name, offset, shape, dtype)
        if self.debug:
            shape_str = 'x'.join(str(s) for s in array.shape)
            print(f"配列読み取り: {name}, 形状={shape_str}, 型={array.dtype}")
        return array
    
    def list_variables(self):
        """
        共有メモリに登録されている変数の一覧を取得
        
        Returns:
            list: 変数名のリスト
        """
        return self.shm_manager.list_variables()
    
    def check_variable_exists(self, name):
        """
        指定された変数が共有メモリに存在するかチェック
        
        Args:
            name (str): 変数名
            
        Returns:
            bool: 変数が存在すればTrue
        """
        return self.shm_manager.check_variable_exists(name)
    
    def wait_for_variable(self, name, timeout=30, check_interval=0.1):
        """
        変数が作成されるまで待機
        
        Args:
            name (str): 変数名
            timeout (float, optional): タイムアウト時間（秒）
            check_interval (float, optional): チェック間隔（秒）
            
        Returns:
            bool: 変数が作成されればTrue、タイムアウトならFalse
        """
        return self.shm_manager.wait_for_variable(name, timeout, check_interval) 