"""
Python-FreeFEM共有メモリ通信ライブラリ

FreeFEMとの通信およびデータ交換を共有メモリを使って行います。
これはSharedMemoryManagerとFreeFEM実行マネージャーを組み合わせた高レベルのAPIです。
"""

import os
import time
import uuid
import tempfile
import numpy as np
from pathlib import Path

from .shm_manager import SharedMemoryManager
from .freefem_runner import FreeFEMRunner
from .data_converter import convert_to_freefem, convert_from_freefem
from .errors import FreeFEMExecutionError, DataTransferError, TimeoutError, FileOperationError
from .utils import ensure_directory, normalize_path

class SharedMemoryCommManager:
    """
    FreeFEMとの共有メモリ通信を管理するクラス
    
    高レベルなAPIを提供し、FreeFEMスクリプトの実行、データの共有メモリ経由での送受信、
    および実行状態の管理を一元的に行います。
    """
    
    def __init__(self, freefem_path=None, shm_size=10*1024*1024, 
                 verbose=False, timeout=60, auto_cleanup=True):
        """
        初期化
        
        Parameters
        ----------
        freefem_path : str, optional
            FreeFEM実行ファイルのパス
        shm_size : int, default=10MB
            共有メモリのサイズ（バイト単位）
        verbose : bool, default=False
            詳細なログ出力を有効にするかどうか
        timeout : float, default=60
            デフォルトのタイムアウト時間（秒）
        auto_cleanup : bool, default=True
            終了時に共有メモリを自動的に削除するかどうか
        """
        self.verbose = verbose
        self.timeout = timeout
        self.auto_cleanup = auto_cleanup
        self.shm_size = shm_size
        
        # 共有メモリの名前（ユニークな名前を生成）
        self.shm_name = f"pyfreefem_{uuid.uuid4().hex}"
        
        # 共有メモリ管理オブジェクトの初期化
        self.shm_manager = SharedMemoryManager(
            name=self.shm_name,
            size=self.shm_size,
            create=True
        )
        
        # FreeFEM実行管理オブジェクトの初期化
        self.freefem_runner = FreeFEMRunner(
            freefem_path=freefem_path,
            verbose=verbose,
            timeout=timeout
        )
        
        # データ保存用の辞書
        self.data = {}
        
        # スクリプト実行の状態
        self.is_running = False
        self.current_script = None
        self.current_process = None
        
        if self.verbose:
            print("SharedMemoryCommManager initialized")
            print(f"共有メモリ名: {self.shm_name}")
            print(f"共有メモリサイズ: {self.shm_size} バイト")
            print(f"FreeFEM実行ファイル: {self.freefem_runner.freefem_path}")
    
    def __del__(self):
        """
        デストラクタ - リソースのクリーンアップ
        """
        self.cleanup()
    
    def cleanup(self):
        """
        リソースのクリーンアップ
        """
        # 実行中のスクリプトを強制終了
        if self.is_running and self.current_process is not None:
            try:
                self.current_process.terminate()
                self.is_running = False
                if self.verbose:
                    print("実行中のスクリプトを強制終了しました")
            except:
                pass
        
        # 共有メモリのクリーンアップ
        if self.auto_cleanup:
            try:
                self.shm_manager.destroy()
                if self.verbose:
                    print(f"共有メモリ '{self.shm_name}' を削除しました")
            except:
                pass
    
    def set_data(self, name, data):
        """
        FreeFEMに送信するデータを設定
        
        Parameters
        ----------
        name : str
            データ名
        data : object
            設定するデータ
            
        Returns
        -------
        bool
            成功した場合はTrue
            
        Raises
        ------
        DataTransferError
            データ形式が無効な場合
        """
        # データを内部辞書に保存
        self.data[name] = data
        
        # データ型に応じて共有メモリに書き込み
        try:
            if isinstance(data, int):
                self.shm_manager.write_int(name, data)
            elif isinstance(data, float):
                self.shm_manager.write_double(name, data)
            elif isinstance(data, str):
                self.shm_manager.write_string(name, data)
            elif isinstance(data, np.ndarray):
                self.shm_manager.write_array(name, data)
            else:
                # その他のデータ型は文字列に変換
                self.shm_manager.write_string(name, str(data))
        except Exception as e:
            raise DataTransferError(f"データの書き込みに失敗しました: {str(e)}")
        
        if self.verbose:
            if isinstance(data, np.ndarray) and data.size > 5:
                preview = f"{data[:5]}... (shape: {data.shape})"
            else:
                preview = str(data)
            print(f"データを設定: {name} = {preview}")
        
        return True
    
    def get_data(self, name, default=None):
        """
        共有メモリから直接データを取得
        
        Parameters
        ----------
        name : str
            データ名
        default : object, optional
            データが存在しない場合のデフォルト値
            
        Returns
        -------
        object
            取得したデータ、または存在しない場合はdefault
        """
        try:
            if not self.shm_manager.check_variable_exists(name):
                return default
            
            # 変数情報を取得してデータ型を判定
            var_info = self.shm_manager._get_var_info(name)
            if var_info is None:
                return default
                
            var_type = var_info['type']
            
            if var_type == 'int':
                data = self.shm_manager.read_int(name)
            elif var_type == 'double':
                data = self.shm_manager.read_double(name)
            elif var_type == 'string':
                data = self.shm_manager.read_string(name)
            elif var_type == 'array':
                data = self.shm_manager.read_array(name)
            else:
                raise DataTransferError(f"未知のデータ型: {var_type}")
                
            # データを内部辞書にも保存
            self.data[name] = data
            return data
            
        except Exception as e:
            if self.verbose:
                print(f"データの取得に失敗しました: {str(e)}")
            return default
    
    def reload_data(self):
        """
        共有メモリからすべての変数を再読み込み
        
        Returns
        -------
        dict
            読み込まれたデータの辞書
        """
        variables = self.shm_manager.list_variables()
        
        for key in variables:
            self.get_data(key)
            
        return self.data
    
    def wait_for_data(self, name, timeout=None):
        """
        特定のデータが共有メモリに書き込まれるのを待つ
        
        Parameters
        ----------
        name : str
            待機するデータ名
        timeout : float, optional
            タイムアウト時間（秒）
            
        Returns
        -------
        object
            取得したデータ
            
        Raises
        ------
        TimeoutError
            タイムアウトした場合
        """
        timeout = timeout or self.timeout
        
        try:
            self.shm_manager.wait_for_variable(name, timeout=timeout)
            return self.get_data(name)
        except Exception as e:
            raise TimeoutError(f"データ '{name}' の待機中にタイムアウトまたはエラーが発生しました: {str(e)}")
    
    def run_script(self, script_path, parameters=None, reload_data=True,
                  verbose_level=0, timeout=None, output_handler=None,
                  working_dir=None, env=None, no_graphics=True):
        """
        FreeFEMスクリプトを実行し、結果を取得
        
        Parameters
        ----------
        script_path : str
            実行するFreeFEMスクリプトのパス
        parameters : dict, optional
            スクリプトに渡すパラメータ
        reload_data : bool, default=True
            スクリプト終了後にデータを再読み込みするかどうか
        verbose_level : int, default=0
            FreeFEMの詳細出力レベル
        timeout : float, optional
            タイムアウト時間（秒）
        output_handler : callable, optional
            出力処理ハンドラー関数 (stdout, stderr) -> None
        working_dir : str, optional
            作業ディレクトリ
        env : dict, optional
            環境変数
        no_graphics : bool, default=True
            グラフィック出力を無効にするかどうか
            
        Returns
        -------
        dict
            実行結果を含む辞書
            
        Raises
        ------
        FreeFEMExecutionError
            実行エラーが発生した場合
        """
        if self.is_running:
            raise FreeFEMExecutionError(
                "他のFreeFEMスクリプトが実行中です",
                script_path=self.current_script
            )
        
        timeout = timeout or self.timeout
        self.current_script = script_path
        
        try:
            self.is_running = True
            
            # FreeFEMプロセスに渡す環境変数を設定
            proc_env = os.environ.copy()
            if env:
                proc_env.update(env)
                
            # 共有メモリ情報を環境変数として渡す
            proc_env["FF_SHM_NAME"] = self.shm_name
            proc_env["FF_SHM_SIZE"] = str(self.shm_size)
            
            # スクリプトに渡すコマンドライン引数の設定
            args = []
            
            # グラフィック表示の制御
            if no_graphics:
                args.extend(["-nw", "-ns"])
                
            # FreeFEMの詳細出力レベル
            if verbose_level > 0:
                args.append(f"-v {verbose_level}")
                
            # スクリプトへのパラメータを追加
            if parameters:
                for k, v in parameters.items():
                    # パラメータの型変換（FreeFEMの形式に合わせる）
                    if isinstance(v, bool):
                        v = 1 if v else 0
                    elif isinstance(v, (list, tuple, np.ndarray)):
                        # リストや配列は渡せないので保存しておく
                        self.set_data(k, v)
                        continue
                        
                    args.append(f"{k}={v}")
            
            # FreeFEMスクリプトを実行
            if self.verbose:
                print(f"FreeFEMスクリプト実行: {script_path}")
                print(f"引数: {args}")
            
            # スクリプトの実行
            exit_code, stdout, stderr = self.freefem_runner.run(
                script_path=script_path,
                args=args,
                env=proc_env,
                working_dir=working_dir,
                timeout=timeout,
                output_handler=output_handler
            )
            
            # 実行結果の確認
            if exit_code != 0:
                raise FreeFEMExecutionError(
                    "FreeFEMの実行に失敗しました",
                    script_path=script_path,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr
                )
                
            # データの再読み込み
            if reload_data:
                self.reload_data()
                
            result = {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "data": self.data.copy()
            }
            
            return result
            
        except Exception as e:
            if not isinstance(e, FreeFEMExecutionError):
                raise FreeFEMExecutionError(
                    f"FreeFEMの実行中にエラーが発生しました: {str(e)}",
                    script_path=script_path
                )
            raise
        finally:
            self.is_running = False
            self.current_process = None
    
    def get_shm_info(self):
        """
        共有メモリの情報を取得
        
        Returns
        -------
        dict
            共有メモリの情報
        """
        return {
            "name": self.shm_name,
            "size": self.shm_size,
            "key": self.shm_manager.key,
            "variables": self.shm_manager.list_variables()
        } 