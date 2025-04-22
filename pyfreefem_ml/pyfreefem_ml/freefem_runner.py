"""
Python-FreeFEM共有データ通信ライブラリのFreeFEM実行モジュール

FreeFEMスクリプトの実行と管理機能を提供します。
"""

import os
import sys
import time
import subprocess
import tempfile
import platform
from pathlib import Path
from .errors import FreeFEMExecutionError, FileOperationError

class FreeFEMRunner:
    """
    FreeFEMスクリプト実行管理クラス
    
    FreeFEMスクリプトを実行し、その結果を管理するためのクラスです。
    """
    
    def __init__(self, freefem_path=None, verbose=False, timeout=60):
        """
        初期化
        
        Parameters
        ----------
        freefem_path : str, optional
            FreeFEM実行ファイルのパス
            Noneの場合は自動検出を試みます
        verbose : bool, default=False
            詳細なログ出力を有効にするかどうか
        timeout : float, default=60
            スクリプト実行のデフォルトタイムアウト時間（秒）
        """
        self.verbose = verbose
        self.timeout = timeout
        self.last_output = None
        self.last_error = None
        self.last_return_code = None
        
        # FreeFEMのパスを設定
        self.freefem_path = freefem_path or self._find_freefem_executable()
        
        if not self.freefem_path:
            if self.verbose:
                print("警告: FreeFEMの実行ファイルが見つかりませんでした。明示的に指定してください。")
        elif self.verbose:
            print(f"FreeFEM実行ファイルのパス: {self.freefem_path}")
    
    def _find_freefem_executable(self):
        """
        FreeFEMの実行ファイルを自動検出

        Returns
        -------
        str or None
            検出されたFreeFEM実行ファイルのパス、見つからない場合はNone
        """
        # 一般的なパスリスト
        possible_paths = [
            # Linuxのパス
            "/usr/bin/FreeFem++",
            "/usr/local/bin/FreeFem++",
            # WSLでのパス
            "/usr/bin/FreeFem++",
            "/usr/local/bin/FreeFem++",
            # Windowsのパス (WSL経由で実行する場合)
            "FreeFem++",
        ]
        
        # 環境変数からFreeFEMのパスを取得
        freefem_env_path = os.environ.get("FREEFEM_PATH")
        if freefem_env_path:
            possible_paths.insert(0, freefem_env_path)
        
        # 各パスでFreeFEMが実行可能かチェック
        for path in possible_paths:
            try:
                # バージョン情報を取得してみる
                if self._is_wsl_environment() and not path.startswith("/"):
                    # WSL環境でWindows上のFreeFEMを使う場合
                    result = subprocess.run(
                        [path, "-v"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                else:
                    # 通常の実行
                    result = subprocess.run(
                        [path, "-v"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                
                if result.returncode == 0 or "FreeFem++" in (result.stdout + result.stderr):
                    return path
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        return None
    
    def _is_wsl_environment(self):
        """
        現在の環境がWSL (Windows Subsystem for Linux) かどうかを判定

        Returns
        -------
        bool
            WSL環境ならTrue、それ以外はFalse
        """
        if platform.system() == "Linux":
            # /proc/versionの内容をチェック
            try:
                with open("/proc/version", "r") as f:
                    version_info = f.read().lower()
                    return "microsoft" in version_info or "wsl" in version_info
            except:
                pass
        
        return False
    
    def _convert_to_wsl_path(self, win_path):
        """
        Windowsパスを WSL パスに変換

        Parameters
        ----------
        win_path : str
            変換するWindowsパス

        Returns
        -------
        str
            変換されたWSLパス
        """
        # 基本的な変換ルール
        # C:\\path\\to\\file.txt -> /mnt/c/path/to/file.txt
        if ":" in win_path:
            drive, rest = win_path.split(":", 1)
            wsl_path = f"/mnt/{drive.lower()}{rest.replace('\\', '/')}"
            return wsl_path
        return win_path
    
    def _convert_to_windows_path(self, wsl_path):
        """
        WSLパスを Windowsパスに変換

        Parameters
        ----------
        wsl_path : str
            変換するWSLパス

        Returns
        -------
        str
            変換されたWindowsパス
        """
        # 基本的な変換ルール
        # /mnt/c/path/to/file.txt -> C:\\path\\to\\file.txt
        if wsl_path.startswith("/mnt/"):
            parts = wsl_path.split("/")
            if len(parts) > 3:
                drive = parts[2].upper()
                rest = "\\".join(parts[3:])
                win_path = f"{drive}:\\{rest}"
                return win_path
        return wsl_path
    
    def run_script(self, script_path, params=None, timeout=None, 
                  working_dir=None, env=None, verbose_level=0,
                  check_mpi=False, no_graphics=True, silent=False):
        """
        FreeFEMスクリプトを実行

        Parameters
        ----------
        script_path : str
            実行するFreeFEMスクリプトのパス
        params : dict, optional
            スクリプトに渡すパラメータ
        timeout : float, optional
            タイムアウト秒数（Noneの場合はインスタンス作成時の設定を使用）
        working_dir : str, optional
            作業ディレクトリ
        env : dict, optional
            環境変数の辞書
        verbose_level : int, default=0
            FreeFEMの詳細出力レベル（0-100）
        check_mpi : bool, default=False
            MPI並列実行を確認するかどうか
        no_graphics : bool, default=True
            グラフィック出力を無効にするかどうか
        silent : bool, default=False
            FreeFEMの標準出力と標準エラー出力を抑制するかどうか
            
        Returns
        -------
        dict
            実行結果を含む辞書
            {
                'success': bool,
                'output': str,
                'error': str,
                'return_code': int
            }
            
        Raises
        ------
        FreeFEMExecutionError
            実行エラーが発生した場合
        FileOperationError
            スクリプトファイルが見つからない場合など
        """
        if not self.freefem_path:
            raise FreeFEMExecutionError(
                "FreeFEM実行ファイルが設定されていません",
                script_path=script_path
            )
        
        if not os.path.exists(script_path):
            raise FileOperationError(
                "スクリプトファイルが見つかりません",
                file_path=script_path,
                operation='read'
            )
        
        # タイムアウト設定
        timeout = timeout or self.timeout
        
        # コマンド構築
        cmd = [self.freefem_path]
        
        # オプション設定
        if verbose_level >= 0:
            cmd.extend(["-v", str(verbose_level)])
        
        if no_graphics:
            cmd.append("-nw")
        
        cmd.append(script_path)
        
        # パラメータの追加
        if params:
            for key, value in params.items():
                cmd.append(f"{key}={value}")
        
        if self.verbose:
            print(f"実行コマンド: {' '.join(cmd)}")
        
        try:
            # 環境変数の準備
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # サブプロセスを実行
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                env=process_env
            )
            
            # タイムアウト付きで完了を待機
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                self.last_output = stdout
                self.last_error = stderr
                self.last_return_code = process.returncode
                
                result = {
                    'success': process.returncode == 0,
                    'output': stdout,
                    'error': stderr,
                    'return_code': process.returncode
                }
                
                if self.verbose:
                    print(f"FreeFEM実行完了: 終了コード {process.returncode}")
                    if not silent:
                        if stdout:
                            print("標準出力:")
                            print(stdout[:500] + ("..." if len(stdout) > 500 else ""))
                        if stderr and process.returncode != 0:
                            print("標準エラー出力:")
                            print(stderr[:500] + ("..." if len(stderr) > 500 else ""))
                
                # エラーチェック（実行自体は成功しても、スクリプト内でエラーが発生する場合がある）
                if process.returncode != 0:
                    raise FreeFEMExecutionError(
                        "FreeFEMスクリプトの実行に失敗しました",
                        script_path=script_path,
                        return_code=process.returncode,
                        stderr=stderr
                    )
                
                return result
                
            except subprocess.TimeoutExpired:
                # タイムアウト発生時はプロセスを強制終了
                process.kill()
                stdout, stderr = process.communicate()
                self.last_output = stdout
                self.last_error = stderr
                self.last_return_code = -1
                
                raise FreeFEMExecutionError(
                    f"FreeFEMスクリプトの実行がタイムアウトしました（{timeout}秒）",
                    script_path=script_path,
                    return_code=-1,
                    stderr="Timeout"
                )
        
        except Exception as e:
            if isinstance(e, FreeFEMExecutionError):
                raise
            
            raise FreeFEMExecutionError(
                f"FreeFEMスクリプトの実行中にエラーが発生しました: {str(e)}",
                script_path=script_path
            ) from e
    
    def create_temp_script(self, script_content, suffix=".edp"):
        """
        一時的なFreeFEMスクリプトファイルを作成

        Parameters
        ----------
        script_content : str
            スクリプトの内容
        suffix : str, default=".edp"
            ファイル名のサフィックス
            
        Returns
        -------
        str
            作成された一時ファイルのパス
            
        Raises
        ------
        FileOperationError
            ファイル作成に失敗した場合
        """
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, 'w') as f:
                f.write(script_content)
            
            if self.verbose:
                print(f"一時スクリプトファイルを作成しました: {temp_path}")
            
            return temp_path
            
        except Exception as e:
            raise FileOperationError(
                f"一時スクリプトファイルの作成に失敗しました: {str(e)}",
                operation='write'
            ) from e
    
    def check_plugin_availability(self, plugin_name, plugin_dir=None):
        """
        FreeFEMプラグインが利用可能かどうかを確認

        Parameters
        ----------
        plugin_name : str
            チェックするプラグイン名（.soや.dllなどの拡張子は不要）
        plugin_dir : str, optional
            プラグインが配置されているディレクトリ
            
        Returns
        -------
        bool
            プラグインが利用可能ならTrue
            
        Raises
        ------
        FreeFEMExecutionError
            FreeFEM実行エラーが発生した場合
        """
        # テストスクリプトを作成
        test_script = f"""
        try {{
            cout << "Checking plugin: {plugin_name}" << endl;
            load "{plugin_name}";
            cout << "Plugin successfully loaded" << endl;
            exit(0);
        }}
        catch(...) {{
            cout << "Plugin failed to load" << endl;
            exit(1);
        }}
        """
        
        # 環境変数の設定
        env = None
        if plugin_dir:
            env = {"FFPP_LOADPATH": plugin_dir}
        
        try:
            # 一時ファイルを作成
            temp_script_path = self.create_temp_script(test_script)
            
            try:
                # スクリプトを実行
                result = self.run_script(
                    temp_script_path,
                    env=env,
                    verbose_level=0,
                    silent=True
                )
                
                return result['success']
                
            finally:
                # 一時ファイルを削除
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                    
        except Exception as e:
            if self.verbose:
                print(f"プラグインチェック中にエラー: {str(e)}")
            return False
    
    def get_freefem_version(self):
        """
        FreeFEMのバージョン情報を取得

        Returns
        -------
        str or None
            バージョン文字列、または取得できない場合はNone
        """
        if not self.freefem_path:
            return None
        
        try:
            result = subprocess.run(
                [self.freefem_path, "-v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            
            # 出力からバージョン情報を抽出
            output = result.stdout + result.stderr
            for line in output.split('\n'):
                if "version" in line.lower():
                    return line.strip()
            
            return output.strip()
            
        except Exception as e:
            if self.verbose:
                print(f"バージョン情報取得中にエラー: {str(e)}")
            return None 