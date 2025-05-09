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
import platform
import numpy as np
from pathlib import Path

# Linuxの場合のみsysv_ipcをインポート
if platform.system() == 'Linux':
    import sysv_ipc

class SharedMemoryManager:
    """共有メモリを管理するクラス"""
    
    def __init__(self, name, size=1024*1024, create=True):
        """初期化処理
        
        Args:
            name (str): 共有メモリの名前
            size (int): 共有メモリのサイズ (バイト単位)
            create (bool): メモリセグメントを新規作成するかどうか
        """
        # 非Linuxプラットフォームでは機能しないが、インポートエラーは防止
        if platform.system() != 'Linux':
            raise RuntimeError("共有メモリ機能はLinux環境でのみサポートされています")
            
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
        # 文字列をUTF-8でエンコード
        encoded = value.encode('utf-8')
        size = len(encoded)
        
        var_info = self._get_var_info(key)
        
        if var_info is None:
            # 新規登録の場合
            offset = self._allocate_memory(size + 4)  # サイズ情報用に4バイト追加
            self._register_var(key, 'string', offset, size + 4)
        else:
            # 更新の場合
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'string':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
            
            # サイズが大きくなった場合は再割り当て
            if size + 4 > var_info['size']:
                offset = self._allocate_memory(size + 4)
                self._register_var(key, 'string', offset, size + 4)
        
        # サイズを書き込み
        self.memory.write(struct.pack('I', size), offset)
        
        # 文字列データを書き込み
        self.memory.write(encoded, offset + 4)
    
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
        
        # サイズを読み込み
        size_data = self.memory.read(4, var_info['offset'])
        size = struct.unpack('I', size_data)[0]
        
        # 文字列データを読み込み
        data = self.memory.read(size, var_info['offset'] + 4)
        return data.decode('utf-8')
    
    def write_array(self, key, array):
        """配列を書き込み
        
        Args:
            key (str): 変数名
            array (numpy.ndarray): 書き込む配列
        """
        # NumPy配列に変換
        if not isinstance(array, np.ndarray):
            array = np.array(array, dtype=np.float64)
        elif array.dtype != np.float64:
            array = array.astype(np.float64)
        
        # 配列のサイズを計算
        size = array.size * 8  # double型は8バイト
        
        var_info = self._get_var_info(key)
        
        if var_info is None:
            # 新規登録の場合
            offset = self._allocate_memory(size + 12)  # サイズと次元数の情報用に12バイト追加
            self._register_var(key, 'array', offset, size + 12)
        else:
            # 更新の場合
            offset = var_info['offset']
            
            # 型チェック
            if var_info['type'] != 'array':
                raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
            
            # サイズが大きくなった場合は再割り当て
            if size + 12 > var_info['size']:
                offset = self._allocate_memory(size + 12)
                self._register_var(key, 'array', offset, size + 12)
        
        # 配列のサイズと次元数を書き込み
        self.memory.write(struct.pack('I', array.size), offset)
        self.memory.write(struct.pack('I', array.ndim), offset + 4)
        self.memory.write(struct.pack('I', array.shape[0]), offset + 8)
        
        # 配列データを書き込み
        self.memory.write(array.tobytes(), offset + 12)
    
    def read_array(self, key):
        """配列を読み込み
        
        Args:
            key (str): 変数名
            
        Returns:
            numpy.ndarray: 読み込んだ配列
        """
        var_info = self._get_var_info(key)
        
        if var_info is None:
            raise KeyError(f"変数 '{key}' は共有メモリ内に存在しません")
        
        # 型チェック
        if var_info['type'] != 'array':
            raise TypeError(f"型の不一致: '{key}' は {var_info['type']} 型として登録されています")
        
        # サイズと次元数を読み込み
        size_data = self.memory.read(4, var_info['offset'])
        ndim_data = self.memory.read(4, var_info['offset'] + 4)
        shape_data = self.memory.read(4, var_info['offset'] + 8)
        
        size = struct.unpack('I', size_data)[0]
        ndim = struct.unpack('I', ndim_data)[0]
        shape = (struct.unpack('I', shape_data)[0],)
        
        # 配列データを読み込み
        data = self.memory.read(size * 8, var_info['offset'] + 12)
        array = np.frombuffer(data, dtype=np.float64)
        
        return array.reshape(shape)
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if hasattr(self, 'memory'):
                self.memory.detach()
                print(f"共有メモリセグメント '{self.name}' (ID: {self.key}) を解放しました")
        except Exception as e:
            print(f"共有メモリの解放中にエラーが発生しました: {str(e)}")
    
    def destroy(self):
        """共有メモリセグメントを完全に削除"""
        try:
            if hasattr(self, 'memory'):
                self.memory.remove()
                print(f"共有メモリセグメント '{self.name}' (ID: {self.key}) を削除しました")
        except Exception as e:
            print(f"共有メモリの削除中にエラーが発生しました: {str(e)}") 