#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreeFEMプラグインインストールモジュール

このモジュールは、FreeFEMの共有メモリプラグインをインストールするための
ユーティリティを提供します。WSL環境でも動作します。
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile
import platform

class PluginInstaller:
    """FreeFEMプラグインをインストールするクラス"""
    
    def __init__(self, debug=False):
        """初期化
        
        Args:
            debug (bool): デバッグモードを有効にするかどうか
        """
        self.debug = debug
        self.is_wsl = self._check_wsl()
        
        # ルートディレクトリの取得
        self.root_dir = Path(__file__).parent.parent
        self.plugin_dir = self.root_dir / "plugins"
        self.script_path = self.plugin_dir / "install_plugin.sh"
        
        # WSL環境で実行する場合のパス変換
        if self.is_wsl:
            if self.debug:
                print("WSL環境が検出されました。パスを変換します...")
            self.wsl_root_dir = self._convert_to_wsl_path(self.root_dir)
            self.wsl_plugin_dir = self._convert_to_wsl_path(self.plugin_dir)
            self.wsl_script_path = self._convert_to_wsl_path(self.script_path)
    
    def _check_wsl(self):
        """WSL環境かどうかをチェック"""
        if platform.system() == "Windows":
            try:
                with open(os.devnull, 'w') as DEVNULL:
                    subprocess.check_call(["wsl", "echo", "test"], stdout=DEVNULL, stderr=DEVNULL)
                return True
            except (subprocess.SubprocessError, FileNotFoundError):
                return False
        return False
    
    def _convert_to_wsl_path(self, windows_path):
        """WindowsパスをWSLパスに変換
        
        Args:
            windows_path (Path): 変換するWindowsパス
            
        Returns:
            str: 変換されたWSLパス
        """
        # パスを文字列に変換して正規化
        path_str = str(windows_path.resolve())
        
        # ドライブレターを取得（例: C:）
        drive = path_str[0].lower()
        
        # パスをWSL形式に変換（例: /mnt/c/path/to/file）
        wsl_path = f"/mnt/{drive}/{path_str[3:].replace('\\', '/')}"
        
        if self.debug:
            print(f"Windows path: {path_str}")
            print(f"WSL path: {wsl_path}")
        
        return wsl_path
    
    def install_plugin(self, force=False):
        """FreeFEMプラグインをインストール
        
        Args:
            force (bool): 既存のプラグインを上書きするかどうか
            
        Returns:
            bool: インストールが成功した場合はTrue
        """
        if not self.script_path.exists():
            print(f"エラー: インストールスクリプトが見つかりません: {self.script_path}")
            return False
        
        print("FreeFEMプラグインのインストールを開始します...")
        
        # WSL環境での実行
        if self.is_wsl:
            return self._install_plugin_wsl(force)
        else:
            return self._install_plugin_native(force)
    
    def _install_plugin_native(self, force=False):
        """ネイティブ環境でプラグインをインストール"""
        try:
            cmd = ["bash", str(self.script_path)]
            if force:
                cmd.append("--force")
            
            if self.debug:
                print(f"実行コマンド: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, cwd=str(self.plugin_dir), check=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
            
            print(result.stdout)
            if result.stderr:
                print(f"警告: {result.stderr}")
            
            return True
        
        except subprocess.CalledProcessError as e:
            print(f"エラー: プラグインのインストールに失敗しました")
            print(f"標準出力: {e.stdout}")
            print(f"エラー出力: {e.stderr}")
            return False
        
        except Exception as e:
            print(f"予期せぬエラーが発生しました: {str(e)}")
            return False
    
    def _install_plugin_wsl(self, force=False):
        """WSL環境でプラグインをインストール"""
        try:
            # WSL内のUbuntuでスクリプトを実行
            cmd = ["wsl", "-d", "Ubuntu", "bash", self.wsl_script_path]
            if force:
                cmd.append("--force")
            
            if self.debug:
                print(f"実行コマンド: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, cwd=str(self.plugin_dir), check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
            
            print(result.stdout)
            if result.stderr:
                print(f"警告: {result.stderr}")
            
            return True
        
        except subprocess.CalledProcessError as e:
            print(f"エラー: WSL環境でのプラグインインストールに失敗しました")
            print(f"標準出力: {e.stdout}")
            print(f"エラー出力: {e.stderr}")
            return False
        
        except Exception as e:
            print(f"予期せぬエラーが発生しました: {str(e)}")
            return False
    
    def check_plugin_installation(self):
        """プラグインがインストールされているかチェック
        
        Returns:
            bool: プラグインがインストールされている場合はTrue
        """
        # FreeFEMのプラグインパスをチェック
        paths_to_check = [
            "/usr/local/lib/ff++/4.10/mmap-semaphore.so",
            "/usr/local/lib/ff++/4.10/lib/mmap-semaphore.so",
            "/usr/lib/ff++/4.10/mmap-semaphore.so",
            "/usr/lib/ff++/4.10/lib/mmap-semaphore.so"
        ]
        
        if self.is_wsl:
            # WSL環境でチェック
            for path in paths_to_check:
                cmd = ["wsl", "-d", "Ubuntu", "test", "-f", path]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if self.debug:
                        print(f"プラグインが見つかりました: {path}")
                    return True
                except subprocess.CalledProcessError:
                    pass
        else:
            # ネイティブ環境でチェック
            for path in paths_to_check:
                if os.path.isfile(path):
                    if self.debug:
                        print(f"プラグインが見つかりました: {path}")
                    return True
        
        if self.debug:
            print("プラグインが見つかりませんでした")
        return False
    
    def setup_environment(self):
        """環境変数を設定
        
        Returns:
            dict: 設定された環境変数
        """
        env_vars = {}
        
        # FreeFEMのライブラリパス
        ff_paths = [
            "/usr/local/lib/ff++/4.10",
            "/usr/lib/ff++/4.10"
        ]
        
        # プラグインが存在するパスを確認
        plugin_path = None
        for path in ff_paths:
            if self.is_wsl:
                cmd = ["wsl", "-d", "Ubuntu", "test", "-f", f"{path}/mmap-semaphore.so"]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    plugin_path = path
                    break
                except subprocess.CalledProcessError:
                    pass
            else:
                if os.path.isfile(f"{path}/mmap-semaphore.so"):
                    plugin_path = path
                    break
        
        if plugin_path:
            env_vars["FF_LOADPATH"] = plugin_path
            env_vars["FF_INCLUDEPATH"] = f"{plugin_path}/idp"
            
            # 環境変数を設定
            os.environ["FF_LOADPATH"] = plugin_path
            os.environ["FF_INCLUDEPATH"] = f"{plugin_path}/idp"
            
            if self.debug:
                print(f"環境変数を設定しました:")
                print(f"  FF_LOADPATH={plugin_path}")
                print(f"  FF_INCLUDEPATH={plugin_path}/idp")
        else:
            print("警告: プラグインパスが見つかりません。環境変数を設定できません。")
        
        return env_vars

def install_plugin(force=False, debug=False):
    """プラグインをインストールする便利な関数
    
    Args:
        force (bool): 既存のプラグインを上書きするかどうか
        debug (bool): デバッグモードを有効にするかどうか
        
    Returns:
        bool: インストールが成功した場合はTrue
    """
    installer = PluginInstaller(debug=debug)
    
    # 既にインストールされている場合はスキップ
    if not force and installer.check_plugin_installation():
        print("プラグインは既にインストールされています。")
        # 環境変数を設定
        installer.setup_environment()
        return True
    
    # インストール実行
    success = installer.install_plugin(force=force)
    
    if success:
        print("プラグインのインストールが完了しました。")
        # 環境変数を設定
        installer.setup_environment()
    
    return success

if __name__ == "__main__":
    # コマンドライン引数の処理
    import argparse
    parser = argparse.ArgumentParser(description="FreeFEMプラグインインストーラー")
    parser.add_argument("--force", action="store_true", help="既存のプラグインを上書きする")
    parser.add_argument("--debug", action="store_true", help="デバッグ出力を有効にする")
    args = parser.parse_args()
    
    # プラグインのインストール実行
    success = install_plugin(force=args.force, debug=args.debug)
    sys.exit(0 if success else 1) 