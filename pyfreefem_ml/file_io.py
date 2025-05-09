#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FreeFEMファイル入出力モジュール

共有メモリの代わりにファイル入出力を使用してFreeFEMとデータを交換するための機能を提供します。
"""

import os
import subprocess
import numpy as np
import platform
import tempfile
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional, Union

class FreeFEMFileIO:
    """FreeFEMとファイル入出力を介して通信するクラス"""
    
    def __init__(self, freefem_path: Union[str, List[str]] = 'FreeFem++', 
                 working_dir: Optional[str] = None,
                 debug: bool = False):
        """
        FreeFEMファイル入出力インターフェースの初期化
        
        Args:
            freefem_path: FreeFEMの実行パス（文字列またはコマンドリスト）
            working_dir: 作業ディレクトリ
            debug: デバッグモード
        """
        self.freefem_path = freefem_path
        self.working_dir = working_dir or os.getcwd()
        self.debug = debug
        self.is_windows = platform.system() == 'Windows'
        self.is_wsl_mode = isinstance(freefem_path, list) and len(freefem_path) > 1 and freefem_path[0] == 'wsl'
    
    def run_script(self, script_path: Union[str, Path], 
                   input_data: Optional[np.ndarray] = None,
                   input_file: str = 'input.txt',
                   output_file: str = 'output.txt',
                   metadata_file: Optional[str] = None) -> Tuple[bool, Optional[np.ndarray], str, str]:
        """
        FreeFEMスクリプトを実行し、ファイル経由でデータを受け渡します
        
        Args:
            script_path: FreeFEMスクリプトのパス
            input_data: FreeFEMに渡す入力データ（省略可能）
            input_file: 入力ファイル名
            output_file: 出力ファイル名
            metadata_file: メタデータファイル名（配列形状情報など）
        
        Returns:
            成功フラグ、出力配列、標準出力、標準エラー出力のタプル
        """
        # WSL環境の場合は特別な処理が必要
        if self.is_windows and self.is_wsl_mode:
            return self._run_script_wsl(script_path, input_data, input_file, output_file, metadata_file)
        
        # 通常の処理（WSL以外）
        return self._run_script_normal(script_path, input_data, input_file, output_file, metadata_file)
    
    def _run_script_normal(self, script_path, input_data, input_file, output_file, metadata_file):
        """通常環境（WSL以外）での実行"""
        # 入力データがあればファイルに書き込む
        if input_data is not None:
            np.savetxt(input_file, input_data)
            if self.debug:
                print(f"入力データをファイルに書き込みました: {input_file}")
        
        # FreeFEMを実行
        script_path = Path(script_path)
        
        # freefem_pathが文字列かリストかを判定
        if isinstance(self.freefem_path, list):
            cmd = self.freefem_path + [str(script_path)]
        else:
            cmd = [self.freefem_path, str(script_path)]
        
        if self.debug:
            print(f"コマンドを実行します: {' '.join(cmd if isinstance(cmd[0], str) else [str(c) for c in cmd])}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.working_dir
        )
        
        # 出力を取得
        stdout, stderr = process.communicate()
        success = process.returncode == 0
        
        if self.debug:
            print(f"FreeFEM実行結果 (コード: {process.returncode})")
            print(stdout)
            if stderr:
                print(f"エラー: {stderr}")
        
        # 実行に失敗した場合
        if not success:
            return False, None, stdout, stderr
        
        # 出力ファイルを読み込む
        if os.path.exists(output_file):
            try:
                # メタデータファイルがある場合は読み込む（多次元配列用）
                if metadata_file and os.path.exists(metadata_file):
                    array = self._load_with_metadata(output_file, metadata_file)
                else:
                    # 単純な1次元配列として読み込む
                    array = np.loadtxt(output_file)
                
                if self.debug:
                    print(f"出力ファイルを読み込みました: {output_file}")
                    print(f"配列の形状: {array.shape}")
                
                return True, array, stdout, stderr
            except Exception as e:
                if self.debug:
                    print(f"出力ファイルの読み込みに失敗しました: {e}")
                return False, None, stdout, stderr
        else:
            if self.debug:
                print(f"出力ファイルが見つかりません: {output_file}")
            return False, None, stdout, stderr
    
    def _run_script_wsl(self, script_path, input_data, input_file, output_file, metadata_file):
        """WSL環境での実行"""
        try:
            # WSLのホームディレクトリを取得
            wsl_home = subprocess.check_output(['wsl', 'echo', '$HOME'], text=True).strip()
            
            # WSL上での一時ディレクトリ作成
            wsl_temp_dir = f"{wsl_home}/temp_pyfreefem"
            subprocess.run(['wsl', 'mkdir', '-p', wsl_temp_dir], check=True)
            
            if self.debug:
                print(f"WSL一時ディレクトリを作成しました: {wsl_temp_dir}")
            
            # スクリプトファイルの内容を取得
            script_content = None
            if os.path.exists(script_path):
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            else:
                return False, None, "", f"スクリプトファイルが見つかりません: {script_path}"
            
            # スクリプトをWSLに書き込み
            wsl_script_path = f"{wsl_temp_dir}/{os.path.basename(script_path)}"
            subprocess.run(['wsl', 'bash', '-c', f"cat > {wsl_script_path} << 'EOF'\n{script_content}\nEOF"], check=True)
            
            if self.debug:
                print(f"スクリプトをWSLに書き込みました: {wsl_script_path}")
            
            # 入力データがあればWSLに書き込み
            if input_data is not None:
                data_string = ' '.join(str(x) for x in input_data.flatten())
                wsl_input_path = f"{wsl_temp_dir}/{input_file}"
                subprocess.run(['wsl', 'bash', '-c', f"echo '{data_string}' > {wsl_input_path}"], check=True)
                
                if self.debug:
                    print(f"入力データをWSLに書き込みました: {wsl_input_path}")
            
            # FreeFEMを実行
            # freefemコマンドを取得 (リストの場合はwslが最初の要素なので除外)
            freefem_cmd = "FreeFem++"
            if isinstance(self.freefem_path, list) and len(self.freefem_path) > 2:
                freefem_cmd = self.freefem_path[-1]
            
            cmd = ['wsl', 'bash', '-c', f"cd {wsl_temp_dir} && {freefem_cmd} {os.path.basename(script_path)}"]
            
            if self.debug:
                print(f"コマンドを実行します: {' '.join(cmd)}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # 結果を取得
            success = process.returncode == 0
            stdout = process.stdout
            stderr = process.stderr
            
            if self.debug:
                print(f"FreeFEM実行結果 (コード: {process.returncode})")
                print(stdout)
                if stderr:
                    print(f"エラー: {stderr}")
            
            # 実行に失敗した場合
            if not success:
                return False, None, stdout, stderr
            
            # 出力ファイルをWSLから読み込む
            array = None
            try:
                # メタデータファイルがある場合
                if metadata_file:
                    # メタデータを読み込む
                    wsl_metadata_path = f"{wsl_temp_dir}/{metadata_file}"
                    metadata_cmd = ['wsl', 'bash', '-c', f"cat {wsl_metadata_path}"]
                    metadata = subprocess.check_output(metadata_cmd, text=True).strip().split('\n')
                    
                    # 出力データを読み込む
                    wsl_output_path = f"{wsl_temp_dir}/{output_file}"
                    output_cmd = ['wsl', 'bash', '-c', f"cat {wsl_output_path}"]
                    output_data = subprocess.check_output(output_cmd, text=True).strip()
                    
                    # メタデータの解析
                    first_line = metadata[0].split()
                    second_line = metadata[1].split()
                    n_functions = int(first_line[0])
                    n_points = int(first_line[1])
                    nx = int(second_line[0])
                    ny = int(second_line[1])
                    
                    # データを解析
                    values = [float(x) for x in output_data.split()]
                    array = np.array(values).reshape((ny, nx))
                    
                    if self.debug:
                        print(f"WSLから多次元配列データを読み込みました: 形状={array.shape}")
                else:
                    # 単純な1次元配列として読み込む
                    wsl_output_path = f"{wsl_temp_dir}/{output_file}"
                    output_cmd = ['wsl', 'bash', '-c', f"cat {wsl_output_path}"]
                    output_data = subprocess.check_output(output_cmd, text=True).strip()
                    values = [float(x) for x in output_data.split()]
                    array = np.array(values)
                    
                    if self.debug:
                        print(f"WSLから1次元配列データを読み込みました: 形状={array.shape}")
                
                return True, array, stdout, stderr
            except Exception as e:
                if self.debug:
                    print(f"WSLからの出力データ読み込みに失敗しました: {e}")
                return False, None, stdout, stderr
        
        except Exception as e:
            if self.debug:
                print(f"WSL実行中にエラーが発生しました: {e}")
            return False, None, "", str(e)
    
    def _load_with_metadata(self, output_file: str, metadata_file: str) -> np.ndarray:
        """
        メタデータを使用して多次元配列を読み込みます
        
        Args:
            output_file: データファイル
            metadata_file: メタデータファイル
        
        Returns:
            適切な形状に変形された多次元配列
        """
        # メタデータを読み込む
        with open(metadata_file, 'r') as f:
            # メタデータの形式に合わせて解析
            lines = f.readlines()
            if len(lines) >= 2:
                # 1行目: 関数の数と各関数の点の数
                first_line = lines[0].strip().split()
                n_functions = int(first_line[0])
                n_points = int(first_line[1])
                
                # 2行目: メッシュの次元
                second_line = lines[1].strip().split()
                nx = int(second_line[0])
                ny = int(second_line[1])
                
                # データを読み込む
                all_data = np.loadtxt(output_file)
                
                # 関数が1つの場合
                if n_functions == 1:
                    return all_data.reshape((ny, nx))
                
                # 複数の関数がある場合、リストに分割
                arrays = []
                offset = 0
                for i in range(n_functions):
                    array_data = all_data[offset:offset + n_points]
                    array_2d = array_data.reshape((ny, nx))
                    arrays.append(array_2d)
                    offset += n_points
                
                # 3次元配列として返す
                return np.array(arrays)
            
            # メタデータの形式が想定と異なる場合は1次元として扱う
            return np.loadtxt(output_file)
