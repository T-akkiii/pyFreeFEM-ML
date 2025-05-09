#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FreeFEMと多次元配列をファイル入出力で交換するテスト
"""

import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def run_freefem_multi_array_test(script_path="multi_array_io_test.edp"):
    """
    FreeFEMスクリプトを実行し、多次元配列データをファイル経由で交換します
    
    Args:
        script_path: FreeFEMスクリプトのパス
        
    Returns:
        成功フラグ、出力配列リスト、メタデータ、標準出力、標準エラー出力
    """
    # FreeFEMを実行（WSL内から直接実行）
    cmd = ['FreeFem++', script_path]
    print(f"コマンドを実行します: {' '.join(cmd)}")
    
    # サブプロセスとしてFreeFEMを実行
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 出力を取得
    stdout, stderr = process.communicate()
    success = process.returncode == 0
    
    # 実行結果を表示
    print(f"FreeFEM実行結果 (コード: {process.returncode}):")
    print(stdout)
    
    if not success:
        print(f"エラー発生: {stderr}")
        return False, None, None, stdout, stderr
    
    # メタデータファイルを読み込む
    metadata_file = "multi_array_metadata.txt"
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r') as f:
                # 1行目: 関数の数と各関数の点の数
                line1 = f.readline().strip().split()
                n_functions = int(line1[0])
                n_points = int(line1[1])
                
                # 2行目: メッシュの次元
                line2 = f.readline().strip().split()
                nx = int(line2[0])
                ny = int(line2[1])
                
                metadata = {
                    'n_functions': n_functions,
                    'n_points': n_points,
                    'nx': nx,
                    'ny': ny
                }
                
                print(f"メタデータを読み込みました:")
                print(f"- 関数の数: {n_functions}")
                print(f"- 各関数の点の数: {n_points}")
                print(f"- メッシュサイズ: {nx}x{ny}")
        except Exception as e:
            print(f"メタデータファイルの読み込みに失敗しました: {e}")
            return False, None, None, stdout, stderr
    else:
        print(f"メタデータファイルが見つかりません: {metadata_file}")
        return False, None, None, stdout, stderr
    
    # 出力ファイルを読み込む
    output_file = "multi_array_output.txt"
    if os.path.exists(output_file):
        try:
            # 出力ファイルから全データを読み込む
            all_data = np.loadtxt(output_file)
            
            # データを関数ごとに分割
            arrays = []
            offset = 0
            for i in range(n_functions):
                # 各関数のデータを抽出
                array_data = all_data[offset:offset + n_points]
                # 2次元配列に変換
                array_2d = array_data.reshape((ny, nx))
                arrays.append(array_2d)
                offset += n_points
            
            print(f"出力ファイルを読み込みました: {output_file}")
            print(f"配列リストの要素数: {len(arrays)}")
            for i, arr in enumerate(arrays):
                print(f"配列{i+1}の形状: {arr.shape}, 最小値: {arr.min():.6f}, 最大値: {arr.max():.6f}")
            
            return True, arrays, metadata, stdout, stderr
        except Exception as e:
            print(f"出力ファイルの読み込みに失敗しました: {e}")
            return False, None, None, stdout, stderr
    else:
        print(f"出力ファイルが見つかりません: {output_file}")
        return False, None, None, stdout, stderr

def plot_multi_arrays(arrays, metadata):
    """
    複数の2次元配列をプロットします
    
    Args:
        arrays: 2次元配列のリスト
        metadata: メタデータ辞書
    """
    n_functions = len(arrays)
    
    # プロットの設定
    fig = plt.figure(figsize=(15, 5 * n_functions))
    titles = [
        "Function 1: x*y",
        "Function 2: sin(2πx)sin(2πy)",
        "Function 3: exp(-10((x-0.5)²+(y-0.5)²))"
    ]
    
    for i, arr in enumerate(arrays):
        # 関数ごとに2つのサブプロット（2Dと3D）を作成
        # 2Dカラーマップ
        ax1 = fig.add_subplot(n_functions, 2, 2*i+1)
        im = ax1.imshow(arr, origin='lower', cmap='viridis')
        plt.colorbar(im, ax=ax1, label='Function value')
        ax1.set_title(f"{titles[i]} (2D)")
        ax1.set_xlabel('X index')
        ax1.set_ylabel('Y index')
        
        # 3Dサーフェイスプロット
        ax2 = fig.add_subplot(n_functions, 2, 2*i+2, projection='3d')
        ny, nx = arr.shape
        x = np.linspace(0, 1, nx)
        y = np.linspace(0, 1, ny)
        X, Y = np.meshgrid(x, y)
        ax2.plot_surface(X, Y, arr, cmap='viridis', edgecolor='none')
        ax2.set_title(f"{titles[i]} (3D)")
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_zlabel('Function value')
    
    plt.tight_layout()
    plt.savefig('multi_array_plots.png')
    print("多次元配列のプロットを保存しました: multi_array_plots.png")
    
    # 表示（GUIが利用可能な場合）
    try:
        plt.show()
    except Exception as e:
        print(f"プロットの表示に失敗しました（ファイルとして保存されています）: {e}")

def main():
    print("FreeFEMと多次元配列をファイル入出力で交換するテストを実行します")
    
    # FreeFEMを実行
    success, arrays, metadata, stdout, stderr = run_freefem_multi_array_test()
    
    if success and arrays is not None:
        print("FreeFEMからの多次元配列の取得に成功しました")
        
        # 配列をプロット
        try:
            plot_multi_arrays(arrays, metadata)
        except Exception as e:
            print(f"プロットの作成に失敗しました: {e}")
    else:
        print("FreeFEMスクリプトの実行に失敗しました")

if __name__ == "__main__":
    main() 