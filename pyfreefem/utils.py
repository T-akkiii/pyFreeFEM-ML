"""
Python-FreeFEM共有データ通信ライブラリのユーティリティモジュール

様々なユーティリティ関数を提供します。
"""

import os
import sys
import platform
import shutil
import tempfile
import json
import numpy as np
from pathlib import Path

def is_wsl_environment():
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

def convert_to_wsl_path(win_path):
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

def convert_to_windows_path(wsl_path):
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

def normalize_path(path, target_os=None):
    """
    パスを現在の環境または指定された環境に合わせて正規化

    Parameters
    ----------
    path : str
        正規化するパス
    target_os : str, optional
        ターゲットOS ('windows', 'linux', 'wsl')
        Noneの場合は現在の環境に合わせて自動判定

    Returns
    -------
    str
        正規化されたパス
    """
    path = str(path)
    
    # ターゲットOSが指定されていない場合は自動判定
    if target_os is None:
        if platform.system() == "Windows":
            target_os = "windows"
        elif is_wsl_environment():
            target_os = "wsl"
        else:
            target_os = "linux"
    
    # 現在のパスの種類を判定
    is_windows_path = ":" in path and "\\" in path
    is_wsl_path = path.startswith("/mnt/") and len(path.split("/")) > 3
    
    # ターゲットに合わせて変換
    if target_os.lower() in ("windows", "win"):
        if is_wsl_path:
            return convert_to_windows_path(path)
        return path
    elif target_os.lower() in ("linux", "wsl"):
        if is_windows_path:
            return convert_to_wsl_path(path)
        return path
    
    # デフォルトでは変換なし
    return path

def ensure_directory(dir_path):
    """
    ディレクトリが存在することを確認し、存在しない場合は作成

    Parameters
    ----------
    dir_path : str
        確認/作成するディレクトリパス

    Returns
    -------
    str
        作成されたディレクトリのパス
    """
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return str(dir_path)

def create_temp_directory(prefix="pyfreefem_"):
    """
    一時ディレクトリを作成

    Parameters
    ----------
    prefix : str, default="pyfreefem_"
        ディレクトリ名のプレフィックス

    Returns
    -------
    str
        作成された一時ディレクトリのパス
    """
    return tempfile.mkdtemp(prefix=prefix)

def save_array_to_file(array, file_path, format="txt"):
    """
    配列をファイルに保存

    Parameters
    ----------
    array : numpy.ndarray
        保存する配列
    file_path : str
        保存先ファイルパス
    format : str, default="txt"
        保存形式 ("txt", "npy", "json", "csv")

    Returns
    -------
    str
        保存されたファイルのパス
    """
    format = format.lower()
    
    if format == "txt" or format == "text":
        np.savetxt(file_path, array)
    elif format == "npy":
        np.save(file_path, array)
    elif format == "json":
        with open(file_path, 'w') as f:
            json.dump(array.tolist(), f)
    elif format == "csv":
        np.savetxt(file_path, array, delimiter=',')
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    return file_path

def load_array_from_file(file_path, format=None):
    """
    ファイルから配列を読み込む

    Parameters
    ----------
    file_path : str
        読み込むファイルのパス
    format : str, optional
        ファイル形式 ("txt", "npy", "json", "csv")
        Noneの場合は拡張子から自動判定

    Returns
    -------
    numpy.ndarray
        読み込まれた配列
    """
    # 形式が指定されていない場合は拡張子から判定
    if format is None:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt":
            format = "txt"
        elif ext == ".npy":
            format = "npy"
        elif ext == ".json":
            format = "json"
        elif ext == ".csv":
            format = "csv"
        else:
            format = "txt"  # デフォルト
    
    format = format.lower()
    
    if format == "txt" or format == "text":
        return np.loadtxt(file_path)
    elif format == "npy":
        return np.load(file_path)
    elif format == "json":
        with open(file_path, 'r') as f:
            return np.array(json.load(f))
    elif format == "csv":
        return np.loadtxt(file_path, delimiter=',')
    else:
        raise ValueError(f"Unsupported format: {format}")

def dict_to_json_file(data, file_path):
    """
    辞書をJSONファイルに保存

    Parameters
    ----------
    data : dict
        保存するデータ
    file_path : str
        保存先ファイルパス

    Returns
    -------
    str
        保存されたファイルのパス
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    return file_path

def json_file_to_dict(file_path):
    """
    JSONファイルから辞書を読み込む

    Parameters
    ----------
    file_path : str
        読み込むファイルのパス

    Returns
    -------
    dict
        読み込まれた辞書
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def find_freefem_executable():
    """
    FreeFEMの実行ファイルを検索

    Returns
    -------
    str or None
        検出されたFreeFEM実行ファイルのパス、見つからない場合はNone
    """
    import subprocess
    
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