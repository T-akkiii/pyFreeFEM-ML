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
import platform
import numpy as np
from pathlib import Path
import uuid

# Linuxの場合のみ共有メモリ関連モジュールをインポート
if platform.system() == 'Linux':
    from .shm_manager import SharedMemoryManager
    from .plugin_installer import install_plugin, PluginInstaller
else:
    # 非Linux環境でのプレースホルダー定義
    class DummyClass:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("この機能はLinux環境でのみサポートされています")
    
    # プレースホルダークラスを定義
    SharedMemoryManager = DummyClass
    PluginInstaller = DummyClass
    
    def install_plugin(*args, **kwargs):
        raise RuntimeError("この機能はLinux環境でのみサポートされています")

class FreeFEMInterface:
    """
    FreeFEMとの通信を行うための高レベルインターフェース
    
    このクラスは共有メモリを使用してPythonとFreeFEMの間でデータをやり取りし、
    FreeFEMスクリプトの実行と結果の取得を容易にします。
    
    注意: Linux環境でのみ共有メモリ機能が使用可能です。
    Windows/macOSでは、代わりにfreefem_ml.PyFreeFEMクラスを使用してください。
    """
    
    def __init__(self, shm_size=1024*1024, wsl_mode=False, debug=False, freefem_path=None, lib_dir=None, auto_install_plugin=True):
        """
        FreeFEMインターフェースを初期化
        
        Args:
            shm_size (int): 共有メモリのサイズ（バイト単位）
            wsl_mode (bool): WSL環境での実行モードを有効にするかどうか
            debug (bool): デバッグモードを有効にするかどうか
            freefem_path (str): FreeFEM実行ファイルのパス（デフォルト: 'FreeFem++'）
            lib_dir (str): FreeFEMライブラリディレクトリのパス
            auto_install_plugin (bool): プラグインの自動インストールを有効にするかどうか
        """
        # 非Linux環境ではエラーを発生させる
        if platform.system() != 'Linux':
            raise RuntimeError("FreeFEMInterface（共有メモリ機能）はLinux環境でのみサポートされています。"
                              "Windows/macOSでは代わりにpyfreefem_ml.PyFreeFEMを使用してください。")
        
        self.debug = debug
        self.wsl_mode = wsl_mode
        self.freefem_path = freefem_path or 'FreeFem++'
        
        # 共有メモリ名として一意のIDを生成
        self.shm_name = f"freefem_shm_{uuid.uuid4().hex[:8]}"
        self.shm_size = shm_size
        
        # プラグインの自動インストール
        if auto_install_plugin:
            self._ensure_plugin_installed()
        
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
    
    def _ensure_plugin_installed(self):
        """プラグインがインストールされていることを確認"""
        if self.debug:
            print("共有メモリプラグインのインストール状態を確認しています...")
        
        # プラグインのインストール状態をチェック
        installer = PluginInstaller(debug=self.debug)
        if not installer.check_plugin_installation():
            if self.debug:
                print("プラグインがインストールされていないため、インストールを開始します...")
            
            # プラグインをインストール
            success = install_plugin(debug=self.debug)
            if not success:
                print("警告: プラグインのインストールに失敗しました。一部の機能が正常に動作しない可能性があります。")
        else:
            if self.debug:
                print("プラグインは既にインストールされています。")
            
            # 環境変数を設定
            installer.setup_environment()
    
    def run_script(self, script_path, timeout=None):
        """
        FreeFEMスクリプトを実行
        
        Args:
            script_path (str): 実行するFreeFEMスクリプトのパス
            timeout (int, optional): 実行タイムアウト（秒）
            
        Returns:
            tuple: (成功フラグ, 標準出力, 標準エラー出力)
        """
        # FreeFEM実行用コマンドを構築
        cmd = [self.freefem_path]
        
        # 環境変数を設定
        env = os.environ.copy()
        env['FF_SHM_NAME'] = self.shm_name
        env['FF_SHM_SIZE'] = str(self.shm_size)
        
        # ライブラリディレクトリが指定されていれば設定
        if self.lib_dir:
            env['FF_INCLUDEPATH'] = self.lib_dir
        
        # プラグインパスが環境変数に設定されていない場合
        if 'FF_LOADPATH' not in env:
            # プラグインインストーラからパス情報を取得
            installer = PluginInstaller(debug=self.debug)
            plugin_env = installer.setup_environment()
            
            # 環境変数を更新
            for key, value in plugin_env.items():
                env[key] = value
        
        # スクリプトパスを追加
        cmd.append(script_path)
        
        if self.debug:
            print(f"実行コマンド: {' '.join(cmd)}")
            print(f"環境変数: SHM_NAME={env.get('FF_SHM_NAME')}, LOADPATH={env.get('FF_LOADPATH')}")
        
        try:
            # WSLモードの場合はwslコマンドを使用
            if self.wsl_mode:
                wsl_cmd = ["wsl", "-d", "Ubuntu", "-e"]
                wsl_cmd.extend(cmd)
                cmd = wsl_cmd
            
            # プロセスを実行
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                universal_newlines=True
            )
            
            # 出力を取得（タイムアウト付き）
            stdout, stderr = process.communicate(timeout=timeout)
            
            # 終了コードをチェック
            success = process.returncode == 0
            if not success and self.debug:
                print(f"FreeFEMスクリプトの実行に失敗: 終了コード {process.returncode}")
                print(f"エラー出力: {stderr}")
            
            return success, stdout, stderr
            
        except subprocess.TimeoutExpired:
            # タイムアウト時はプロセスを終了
            process.kill()
            stdout, stderr = process.communicate()
            print(f"FreeFEMスクリプトの実行がタイムアウトしました（{timeout}秒）")
            return False, stdout, stderr
            
        except Exception as e:
            print(f"FreeFEMスクリプトの実行中にエラーが発生しました: {str(e)}")
            return False, "", str(e)
    
    def run_inline_script(self, script_content, timeout=None):
        """
        インラインFreeFEMスクリプトを実行
        
        Args:
            script_content (str): 実行するFreeFEMスクリプト内容
            timeout (int, optional): 実行タイムアウト（秒）
            
        Returns:
            tuple: (成功フラグ, 標準出力, 標準エラー出力)
        """
        # プリアンブルを追加（共有メモリプラグインのロードなど）
        preamble = """
        // mmap-semaphoreプラグインのロード
        load "mmap-semaphore"
        """
        
        full_script = preamble + script_content
        
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.edp', mode='w', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(full_script)
            tmp_path = tmp_file.name
        
        try:
            # 一時ファイルを実行
            result = self.run_script(tmp_path, timeout)
            return result
        finally:
            # 一時ファイルを削除
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    # ==== データ書き込みメソッド ====
    
    def write_int(self, name, value):
        """
        整数値を共有メモリに書き込み
        
        Args:
            name (str): 変数名
            value (int): 書き込む整数値
        """
        self.shm_manager.write_int(name, int(value))
        if self.debug:
            print(f"整数書き込み: {name} = {value}")
    
    def write_double(self, name, value):
        """
        実数値を共有メモリに書き込み
        
        Args:
            name (str): 変数名
            value (float): 書き込む実数値
        """
        self.shm_manager.write_double(name, float(value))
        if self.debug:
            print(f"実数書き込み: {name} = {value}")
    
    def write_string(self, name, value):
        """
        文字列を共有メモリに書き込み
        
        Args:
            name (str): 変数名
            value (str): 書き込む文字列
        """
        self.shm_manager.write_string(name, str(value))
        if self.debug:
            print(f"文字列書き込み: {name} = {value}")
    
    def write_array(self, name, array):
        """
        配列を共有メモリに書き込み
        
        Args:
            name (str): 変数名
            array (numpy.ndarray or list): 書き込む配列
        """
        # NumPy配列に変換
        if not isinstance(array, np.ndarray):
            array = np.array(array, dtype=np.float64)
        elif array.dtype != np.float64:
            array = array.astype(np.float64)
        
        self.shm_manager.write_array(name, array)
        if self.debug:
            print(f"配列書き込み: {name} = {array}")
    
    def write_int_array(self, array, name):
        """
        整数配列を共有メモリに書き込み
        
        Args:
            array (numpy.ndarray or list): 書き込む整数配列
            name (str): 変数名
        """
        self.shm_manager.write_int_array(name, array)
        if self.debug:
            shape_str = 'x'.join(str(s) for s in (array.shape if hasattr(array, 'shape') else [len(array)]))
            print(f"整数配列書き込み: {name}, 形状={shape_str}")
    
    def write_double_array(self, array, name):
        """
        浮動小数点配列（double型）を共有メモリに書き込み

        Args:
            array (numpy.ndarray): 書き込む浮動小数点配列（dtype=np.float64推奨）
            name (str): 変数名
        """
        # float64型に変換
        if array.dtype != np.float64:
            array = array.astype(np.float64)
        
        self.shm_manager.write_array(array, name)
        if self.debug:
            shape_str = 'x'.join(str(s) for s in array.shape)
            print(f"浮動小数点配列書き込み: {name}, 形状={shape_str}")
    
    def write_matrix(self, matrix, name):
        """
        2次元配列（行列）を共有メモリに書き込み
        
        Args:
            matrix (numpy.ndarray): 書き込む2次元配列
            name (str): 変数名
        """
        # 2次元配列であることを確認
        if len(matrix.shape) != 2:
            raise ValueError(f"入力は2次元配列である必要があります。現在の次元数: {len(matrix.shape)}")
        
        # float64型に変換
        if matrix.dtype != np.float64:
            matrix = matrix.astype(np.float64)
        
        self.shm_manager.write_array(name, matrix)
        if self.debug:
            rows, cols = matrix.shape
            print(f"行列書き込み: {name}, 形状={rows}x{cols}, 型={matrix.dtype}")
    
    def write_int_matrix(self, matrix, name):
        """
        整数行列を共有メモリに書き込み
        
        Args:
            matrix (numpy.ndarray): 書き込む整数行列
            name (str): 変数名
        """
        # 2次元配列であることを確認
        if len(matrix.shape) != 2:
            raise ValueError(f"入力は2次元配列である必要があります。現在の次元数: {len(matrix.shape)}")
        
        # int32型に変換
        if matrix.dtype != np.int32:
            matrix = matrix.astype(np.int32)
        
        self.shm_manager.write_int_array(name, matrix)
        if self.debug:
            rows, cols = matrix.shape
            print(f"整数行列書き込み: {name}, 形状={rows}x{cols}")
    
    # ==== データ読み取りメソッド ====
    
    def read_int(self, name):
        """
        整数値を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            int: 読み込んだ整数値
        """
        value = self.shm_manager.read_int(name)
        if self.debug:
            print(f"整数読み込み: {name} = {value}")
        return value
    
    def read_double(self, name):
        """
        実数値を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            float: 読み込んだ実数値
        """
        value = self.shm_manager.read_double(name)
        if self.debug:
            print(f"実数読み込み: {name} = {value}")
        return value
    
    def read_string(self, name):
        """
        文字列を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            str: 読み込んだ文字列
        """
        value = self.shm_manager.read_string(name)
        if self.debug:
            print(f"文字列読み込み: {name} = {value}")
        return value
    
    def read_array(self, name):
        """
        配列を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだ配列
        """
        array = self.shm_manager.read_array(name)
        if self.debug:
            print(f"配列読み込み: {name} = {array}")
        return array
    
    def read_int_array(self, name):
        """
        整数配列を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだ整数配列
        """
        array = self.shm_manager.read_int_array(name)
        if self.debug:
            shape_str = 'x'.join(str(s) for s in array.shape)
            print(f"整数配列読み込み: {name}, 形状={shape_str}")
        return array
    
    def read_double_array(self, name):
        """
        浮動小数点配列（double型）を共有メモリから読み込み

        Args:
            name (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだ浮動小数点配列（dtype=np.float64）
        """
        array = self.shm_manager.read_array(name, dtype=np.float64)
        if self.debug:
            shape_str = 'x'.join(str(s) for s in array.shape)
            print(f"浮動小数点配列読み込み: {name}, 形状={shape_str}")
        return array
    
    def read_matrix(self, name):
        """
        2次元配列（行列）を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだ2次元配列
        """
        matrix = self.shm_manager.read_array(name, dtype=np.float64)
        
        # 配列が2次元でない場合、可能であれば2次元に変換
        if len(matrix.shape) != 2:
            if len(matrix.shape) == 1:
                # 1次元配列の場合、列ベクトルとして扱う
                matrix = matrix.reshape(-1, 1)
            else:
                raise ValueError(f"2次元行列として読み込れません。現在の次元数: {len(matrix.shape)}")
        
        if self.debug:
            rows, cols = matrix.shape
            print(f"行列読み込み: {name}, 形状={rows}x{cols}")
        
        return matrix
    
    def read_int_matrix(self, name):
        """
        整数行列を共有メモリから読み込み
        
        Args:
            name (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだ整数行列
        """
        matrix = self.shm_manager.read_int_array(name)
        
        # 配列が2次元でない場合、可能であれば2次元に変換
        if len(matrix.shape) != 2:
            if len(matrix.shape) == 1:
                # 1次元配列の場合、列ベクトルとして扱う
                matrix = matrix.reshape(-1, 1)
            else:
                raise ValueError(f"2次元行列として読み込れません。現在の次元数: {len(matrix.shape)}")
        
        if self.debug:
            rows, cols = matrix.shape
            print(f"整数行列読み込み: {name}, 形状={rows}x{cols}")
        
        return matrix
    
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