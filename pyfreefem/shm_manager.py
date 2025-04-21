#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PyFreeFEM共有メモリマネージャー
このモジュールは、FreeFEMとPython間の共有メモリ通信を管理します。
"""

import os
import sys
import json
import time
import struct
import sysv_ipc
import numpy as np
from pathlib import Path

class SharedMemoryManager:
    """共有メモリを管理するクラス"""
    
    def __init__(self, name, size=1024*1024, create=True):
        """初期化処理
        
        Args:
            name (str): 共有メモリの名前
            size (int): 共有メモリのサイズ (バイト単位)
            create (bool): メモリセグメントを新規作成するかどうか
        """
        self.name = name
        self.size = size
        
        # キーを生成（名前からハッシュ値を生成）
        self.key = self._generate_key_from_name(name)
        
        # ヘッダーサイズ（メタデータ用）
        self.header_size = 1024  # 最初の1KBはヘッダー情報用に予約
        
        # データ領域の開始位置
        self.data_offset = self.header_size
        
        # メタデータの初期化
        self.metadata = {}
        
        try:
            if create:
                # 共有メモリセグメントを作成
                self.memory = sysv_ipc.SharedMemory(
                    self.key, 
                    sysv_ipc.IPC_CREAT | 0o666, 
                    size=self.size
                )
                self._init_header()
            else:
                # 既存の共有メモリセグメントに接続
                self.memory = sysv_ipc.SharedMemory(self.key)
                self._load_header()
                
            print(f"共有メモリセグメント '{name}' (ID: {self.key}) に接続しました")
        
        except Exception as e:
            raise RuntimeError(f"共有メモリの初期化に失敗しました: {str(e)}")
    
    def _generate_key_from_name(self, name):
        """名前からIPCキーを生成する
        
        Args:
            name (str): 共有メモリの名前
        
        Returns:
            int: 生成されたキー値
        """
        # 単純なハッシュ関数 (より堅牢な実装では、一貫性のあるハッシュ関数を使用)
        hash_value = 0
        for char in name:
            hash_value = (hash_value * 31 + ord(char)) & 0x7fffffff
        
        # キーが0の場合は使用できないため、1を加算
        if hash_value == 0:
            hash_value = 1
            
        return hash_value
    
    def _init_header(self):
        """ヘッダー情報を初期化"""
        self.metadata = {
            'version': '1.0',
            'create_time': time.time(),
            'name': self.name,
            'variables': {}
        }
        self._save_header()
    
    def _save_header(self):
        """ヘッダー情報を保存"""
        header_json = json.dumps(self.metadata).encode('utf-8')
        
        # ヘッダーサイズを超えないようにチェック
        if len(header_json) >= self.header_size:
            raise ValueError(f"ヘッダー情報が大きすぎます ({len(header_json)} バイト > {self.header_size} バイト)")
        
        # ヘッダー情報の長さを保存 (最初の4バイト)
        self.memory.write(struct.pack('I', len(header_json)), 0)
        
        # ヘッダー情報自体を保存 (4バイト目以降)
        self.memory.write(header_json, 4)
    
    def _load_header(self):
        """ヘッダー情報を読み込み"""
        # ヘッダー情報の長さを読み込み
        header_len_bytes = self.memory.read(4, 0)
        header_len = struct.unpack('I', header_len_bytes)[0]
        
        # ヘッダー情報を読み込み
        header_json = self.memory.read(header_len, 4)
        self.metadata = json.loads(header_json.decode('utf-8'))
    
    def _get_var_info(self, key):
        """変数情報を取得
        
        Args:
            key (str): 変数名
            
        Returns:
            dict: 変数情報（存在しない場合はNone）
        """
        self._load_header()  # 最新のメタデータを読み込み
        return self.metadata['variables'].get(key)
    
    def _register_var(self, key, var_type, offset, size):
        """変数を登録
        
        Args:
            key (str): 変数名
            var_type (str): データ型
            offset (int): オフセット位置
            size (int): サイズ（バイト）
        """
        self._load_header()  # 最新のメタデータを読み込み
        
        self.metadata['variables'][key] = {
            'type': var_type,
            'offset': offset,
            'size': size,
            'update_time': time.time()
        }
        
        self._save_header()
    
    def _allocate_memory(self, size):
        """メモリ領域を確保
        
        Args:
            size (int): 必要なバイトサイズ
            
        Returns:
            int: 割り当てられたオフセット位置
        """
        self._load_header()  # 最新のメタデータを読み込み
        
        # 変数情報から使用済みの最大オフセットを特定
        max_offset = self.data_offset
        for var in self.metadata['variables'].values():
            var_end = var['offset'] + var['size']
            if var_end > max_offset:
                max_offset = var_end
        
        # 新しいオフセット位置（メモリ内の次の利用可能なスペース）
        new_offset = max_offset
        
        # メモリ境界を考慮し8バイト境界に合わせる
        if new_offset % 8 != 0:
            new_offset += 8 - (new_offset % 8)
        
        # メモリ容量を超えていないか確認
        if new_offset + size > self.size:
            raise MemoryError(f"共有メモリの容量不足です (必要: {new_offset + size}, 利用可能: {self.size})")
        
        return new_offset
    
    def write_int(self, key, value):
        """整数値を書き込み
        
        Args:
            key (str): 変数名
            value (int): 整数値
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            # 新規登録の場合
            offset = self._allocate_memory(4)
            self._register_var(key, 'int', offset, 4)
        else:
            # 更新の場合
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'int':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 値を書き込み
        self.memory.write(struct.pack('i', value), offset)
    
    def read_int(self, key):
        """整数値を読み込み
        
        Args:
            key (str): 変数名
            
        Returns:
            int: 読み込んだ整数値
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            raise KeyError(f"変数 '{key}' は共有メモリ内に存在しません")
        
        # 型チェック
        if var_info['type'] != 'int':
            raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 値を読み込み
        data = self.memory.read(4, var_info['offset'])
        return struct.unpack('i', data)[0]
    
    def write_double(self, key, value):
        """浮動小数点値を書き込み
        
        Args:
            key (str): 変数名
            value (float): 浮動小数点値
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            # 新規登録の場合
            offset = self._allocate_memory(8)
            self._register_var(key, 'double', offset, 8)
        else:
            # 更新の場合
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'double':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 値を書き込み
        self.memory.write(struct.pack('d', value), offset)
    
    def read_double(self, key):
        """浮動小数点値を読み込み
        
        Args:
            key (str): 変数名
            
        Returns:
            float: 読み込んだ浮動小数点値
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            raise KeyError(f"変数 '{key}' は共有メモリ内に存在しません")
        
        # 型チェック
        if var_info['type'] != 'double':
            raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 値を読み込み
        data = self.memory.read(8, var_info['offset'])
        return struct.unpack('d', data)[0]
    
    def write_string(self, key, value):
        """文字列を書き込み
        
        Args:
            key (str): 変数名
            value (str): 文字列
        """
        # 文字列をバイト列に変換
        byte_data = value.encode('utf-8')
        data_size = len(byte_data) + 4  # サイズ情報を含む
        
        var_info = self._get_var_info(key)
        
        if var_info is None or var_info['size'] < data_size:
            # 新規登録または既存の領域が小さい場合は再割り当て
            offset = self._allocate_memory(data_size)
            self._register_var(key, 'string', offset, data_size)
        else:
            # 既存の領域が十分な大きさの場合は更新
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'string':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 文字列の長さを書き込み
        self.memory.write(struct.pack('I', len(byte_data)), offset)
        
        # 文字列データを書き込み
        self.memory.write(byte_data, offset + 4)
    
    def read_string(self, key):
        """文字列を読み込み
        
        Args:
            key (str): 変数名
            
        Returns:
            str: 読み込んだ文字列
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            raise KeyError(f"変数 '{key}' は共有メモリ内に存在しません")
        
        # 型チェック
        if var_info['type'] != 'string':
            raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 文字列の長さを読み込み
        length_data = self.memory.read(4, var_info['offset'])
        length = struct.unpack('I', length_data)[0]
        
        # 文字列データを読み込み
        string_data = self.memory.read(length, var_info['offset'] + 4)
        return string_data.decode('utf-8')
    
    def write_array(self, key, array, dtype='double'):
        """NumPy配列を書き込み
        
        Args:
            key (str): 変数名
            array (numpy.ndarray): NumPy配列
            dtype (str): データ型（'double'または'int'）
        """
        # 変換されたデータのバイト列
        if dtype == 'double':
            byte_data = array.astype(np.float64).tobytes()
            element_size = 8
        elif dtype == 'int':
            byte_data = array.astype(np.int32).tobytes()
            element_size = 4
        else:
            raise ValueError(f"サポートされていないデータ型: {dtype}")
        
        # 形状情報をエンコード
        shape_info = np.array(array.shape, dtype=np.int32)
        shape_bytes = shape_info.tobytes()
        
        # メタデータサイズ: shapeの次元数(4バイト) + 各次元のサイズ + データ型(4バイト)
        metadata_size = 4 + len(shape_bytes) + 4
        total_size = metadata_size + len(byte_data)
        
        var_info = self._get_var_info(key)
        
        if var_info is None or var_info['size'] < total_size:
            # 新規登録または既存の領域が小さい場合は再割り当て
            offset = self._allocate_memory(total_size)
            self._register_var(key, 'array', offset, total_size)
        else:
            # 既存の領域が十分な大きさの場合は更新
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'array':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 次元数を書き込み
        self.memory.write(struct.pack('I', len(array.shape)), offset)
        current_offset = offset + 4
        
        # 形状情報を書き込み
        self.memory.write(shape_bytes, current_offset)
        current_offset += len(shape_bytes)
        
        # データ型情報を書き込み (0: int, 1: double)
        dtype_code = 1 if dtype == 'double' else 0
        self.memory.write(struct.pack('I', dtype_code), current_offset)
        current_offset += 4
        
        # 配列データを書き込み
        self.memory.write(byte_data, current_offset)
    
    def read_array(self, key):
        """NumPy配列を読み込み
        
        Args:
            key (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだNumPy配列
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            raise KeyError(f"変数 '{key}' は共有メモリ内に存在しません")
        
        # 型チェック
        if var_info['type'] != 'array':
            raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # 次元数を読み込み
        ndim_data = self.memory.read(4, var_info['offset'])
        ndim = struct.unpack('I', ndim_data)[0]
        current_offset = var_info['offset'] + 4
        
        # 形状情報を読み込み
        shape_bytes = self.memory.read(ndim * 4, current_offset)
        shape = np.frombuffer(shape_bytes, dtype=np.int32)
        current_offset += ndim * 4
        
        # データ型情報を読み込み
        dtype_data = self.memory.read(4, current_offset)
        dtype_code = struct.unpack('I', dtype_data)[0]
        dtype = np.float64 if dtype_code == 1 else np.int32
        element_size = 8 if dtype_code == 1 else 4
        current_offset += 4
        
        # 配列の総要素数を計算
        total_elements = np.prod(shape)
        
        # 配列データを読み込み
        array_bytes = self.memory.read(total_elements * element_size, current_offset)
        array = np.frombuffer(array_bytes, dtype=dtype)
        
        # 元の形状に変換
        return array.reshape(shape)
    
    def list_variables(self):
        """登録されている変数一覧を取得
        
        Returns:
            dict: 変数情報の辞書
        """
        self._load_header()  # 最新のメタデータを読み込み
        return self.metadata['variables']
    
    def check_variable_exists(self, key):
        """変数が存在するかチェック
        
        Args:
            key (str): 変数名
            
        Returns:
            bool: 存在する場合はTrue
        """
        return self._get_var_info(key) is not None
    
    def wait_for_variable(self, key, timeout=60):
        """変数が作成されるまで待機
        
        Args:
            key (str): 変数名
            timeout (int): タイムアウト時間（秒）
            
        Returns:
            bool: 変数が作成された場合はTrue、タイムアウトした場合はFalse
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.check_variable_exists(key):
                return True
            time.sleep(0.1)  # 100ミリ秒待機
        
        return False
    
    def write_double_array(self, start_index, values):
        """複数の浮動小数点値を連続したインデックスに一度に書き込み
        
        Args:
            start_index (int): 開始インデックス
            values (array-like): 書き込む値の配列（NumPy配列またはリスト）
        """
        # NumPy配列に変換
        if not isinstance(values, np.ndarray):
            values = np.array(values, dtype=np.float64)
        else:
            values = values.astype(np.float64)
        
        # 各インデックスごとに値が登録されているか確認
        for i in range(len(values)):
            key = start_index + i
            var_info = self._get_var_info(str(key))
            
            if var_info is None:
                # 新規登録の場合
                offset = self._allocate_memory(8)
                self._register_var(str(key), 'double', offset, 8)
        
        # 高速化のため、各値を直接書き込む
        for i, value in enumerate(values):
            key = start_index + i
            var_info = self._get_var_info(str(key))
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'double':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
            
            # 値を書き込み
            self.memory.write(struct.pack('d', value), offset)
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            # メモリセグメントを解放
            self.memory.detach()
            print(f"共有メモリセグメント '{self.name}' (ID: {self.key}) を解放しました")
        except Exception as e:
            print(f"共有メモリの解放中にエラーが発生しました: {str(e)}")
    
    def destroy(self):
        """共有メモリセグメントを破棄"""
        try:
            self.memory.remove()
            print(f"共有メモリセグメント '{self.name}' (ID: {self.key}) を破棄しました")
        except Exception as e:
            print(f"共有メモリの破棄中にエラーが発生しました: {str(e)}") 