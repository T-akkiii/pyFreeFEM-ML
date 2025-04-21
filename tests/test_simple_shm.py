#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共有メモリの基本テスト
sysv_ipc機能を使用した共有メモリの作成・読み書きをテストします
"""

import os
import sys
import json
import time
import struct
import sysv_ipc
import numpy as np
import subprocess
import tempfile

def is_wsl():
    """WSL環境かどうかを判定"""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

def get_page_size():
    """システムのページサイズを取得"""
    try:
        # Linux系OSのみ
        import resource
        return resource.getpagesize()
    except (ImportError, AttributeError):
        # デフォルトのページサイズ (多くのシステムで4KB)
        return 4096

def align_size_to_page(size):
    """サイズをページサイズの倍数に調整"""
    page_size = get_page_size()
    return ((size + page_size - 1) // page_size) * page_size

def safe_shm_create(key, size_request, max_tries=10):
    """安全に共有メモリを作成する
    
    サイズが無効な場合、サイズを減らして再試行します
    
    Args:
        key: 共有メモリのキー
        size_request: 最初に要求するサイズ
        max_tries: 最大試行回数
        
    Returns:
        tuple: (成功した共有メモリオブジェクト, 実際のサイズ)
    """
    size = size_request
    page_size = get_page_size()
    
    # WSLかどうかを確認
    wsl_env = is_wsl()
    if wsl_env:
        print("WSL環境を検出しました。代替手段を使用します。")
        return use_file_based_shm(key, size_request)
    
    for attempt in range(max_tries):
        try:
            # サイズがページサイズの倍数になっていることを確認
            if size % page_size != 0:
                size = (size // page_size) * page_size
                if size == 0:
                    size = page_size
            
            print(f"試行 {attempt+1}/{max_tries}: サイズ = {size} バイト")
            shm = sysv_ipc.SharedMemory(key, sysv_ipc.IPC_CREAT, size=size, mode=0o666)
            return shm, size
        except ValueError as e:
            if "size is invalid" in str(e) or "The size is invalid" in str(e):
                # サイズを半分にして再試行
                old_size = size
                size = max(page_size, size // 2)
                print(f"サイズが無効です ({old_size} バイト)。サイズを {size} バイトに減らして再試行します。")
                continue
            else:
                # その他のエラーは再試行しない
                raise
    
    raise ValueError(f"{max_tries}回試行しましたが、有効なサイズが見つかりませんでした")

def use_file_based_shm(key, size):
    """WSL環境用の代替手段: ファイルベースの共有メモリエミュレーション"""
    # 一時ディレクトリを作成またはパス取得
    temp_dir = os.path.join(tempfile.gettempdir(), 'pyfreefem_shm')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 共有メモリファイルパス
    shm_file = os.path.join(temp_dir, f'shm_{key}.bin')
    
    # ファイルベースのメモリマップ
    class FileBasedSharedMemory:
        def __init__(self, filename, size):
            self.filename = filename
            self.size = size
            # ファイルが存在しない場合は作成し、サイズを設定
            if not os.path.exists(filename) or os.path.getsize(filename) < size:
                with open(filename, 'wb') as f:
                    f.write(b'\0' * size)
            self.file = open(filename, 'r+b')
        
        def read(self, nbytes, offset=0):
            self.file.seek(offset)
            return self.file.read(nbytes)
        
        def write(self, data, offset=0):
            self.file.seek(offset)
            self.file.write(data)
            self.file.flush()
        
        def close(self):
            if hasattr(self, 'file') and self.file:
                self.file.close()
        
        def __del__(self):
            self.close()
    
    # 共有ファイルオブジェクトの作成
    shm = FileBasedSharedMemory(shm_file, size)
    print(f"ファイルベースの共有メモリを作成しました: {shm_file}, サイズ = {size} バイト")
    
    return shm, size

def main():
    """共有メモリの基本機能テスト"""
    print("共有メモリ基本テスト開始")
    
    key = 12345
    
    # ページサイズの取得と出力
    page_size = get_page_size()
    print(f"システムのページサイズ: {page_size} バイト")
    
    try:
        # サイズを小さく設定
        initial_size = 16 * 1024  # 16KB
        print(f"要求サイズ: {initial_size} バイト")
        
        # 安全に共有メモリを作成
        shm, actual_size = safe_shm_create(key, initial_size)
        print(f"共有メモリを作成しました: key={key}, size={actual_size} バイト")
        
        # 基本的なデータ書き込み
        message = "Hello from shared memory!"
        shm.write(message.encode())
        print(f"メッセージを書き込みました: {message}")
        
        # 読み込みテスト
        read_bytes = shm.read(len(message))
        read_message = read_bytes.decode()
        print(f"メッセージを読み込みました: {read_message}")
        
        # 構造化データテスト
        data = {
            "int_value": 42,
            "float_value": 3.14159,
            "string_value": "テストデータ",
            "timestamp": time.time()
        }
        
        # JSONに変換してバイト列に変換
        json_data = json.dumps(data).encode()
        
        # JSON長さとJSONデータを書き込み
        offset1 = 100  # オフセット位置
        shm.write(struct.pack('I', len(json_data)), offset=offset1)
        shm.write(json_data, offset=offset1 + 4)
        print(f"構造化データを書き込みました: {data}")
        
        # JSON長さを読み込み
        json_len_bytes = shm.read(4, offset=offset1)
        json_len = struct.unpack('I', json_len_bytes)[0]
        
        # JSONデータを読み込み
        json_bytes = shm.read(json_len, offset=offset1 + 4)
        read_data = json.loads(json_bytes.decode())
        print(f"構造化データを読み込みました: {read_data}")
        
        # NumPy配列テスト（小さいサイズに抑える）
        array = np.array([1.1, 2.2, 3.3], dtype=np.float64)  # 要素数を減らす
        array_bytes = array.tobytes()
        
        # 配列サイズと配列データを書き込み
        offset2 = 500  # オフセット位置
        shm.write(struct.pack('I', len(array_bytes)), offset=offset2)
        shm.write(array_bytes, offset=offset2 + 4)
        print(f"NumPy配列を書き込みました: {array}")
        
        # 配列サイズを読み込み
        array_size_bytes = shm.read(4, offset=offset2)
        array_size = struct.unpack('I', array_size_bytes)[0]
        
        # 配列データを読み込み
        array_bytes = shm.read(array_size, offset=offset2 + 4)
        read_array = np.frombuffer(array_bytes, dtype=np.float64)
        print(f"NumPy配列を読み込みました: {read_array}")
        
        # 検証
        assert read_message == message, "メッセージの検証に失敗しました"
        assert read_data["int_value"] == data["int_value"], "整数値の検証に失敗しました"
        assert abs(read_data["float_value"] - data["float_value"]) < 1e-10, "浮動小数点値の検証に失敗しました"
        assert read_data["string_value"] == data["string_value"], "文字列値の検証に失敗しました"
        assert np.array_equal(read_array, array), "配列の検証に失敗しました"
        
        print("すべての検証に成功しました！")
        
        # テスト結果をファイルに保存
        with open("python_shm_test_result.txt", "w") as f:
            f.write("共有メモリテスト結果: 成功\n")
            f.write(f"メッセージ: {message}\n")
            f.write(f"構造化データ: {data}\n")
            f.write(f"NumPy配列: {array}\n")
            f.write(f"共有メモリサイズ: {actual_size} バイト\n")
            # WSL環境の場合はその旨記録
            if is_wsl():
                f.write("注意: WSL環境ではファイルベースの共有メモリエミュレーションを使用しています\n")
        
        print("テスト結果をファイルに保存しました: python_shm_test_result.txt")
        
        # 最終的なサイズを共有メモリに保存
        shm.write(struct.pack('I', actual_size), offset=8)
        print(f"共有メモリサイズ情報を保存しました: {actual_size} バイト (オフセット8)")
        
        return 0
    
    except Exception as e:
        print(f"テスト中にエラーが発生しました: {e}")
        import traceback
        print(traceback.format_exc())
        return 1
    
    finally:
        # 注意: テスト時には共有メモリを明示的に削除しない
        # 本番環境では適切に管理する必要があります
        print("共有メモリはテスト用に保持されます")

if __name__ == "__main__":
    sys.exit(main()) 