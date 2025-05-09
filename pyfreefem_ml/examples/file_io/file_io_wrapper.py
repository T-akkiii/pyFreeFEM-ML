#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FreeFEMとファイル入出力で通信するテスト
"""

import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def run_freefem_with_file_io(script_path, input_array=None, output_file='output.txt'):
    """
    FreeFEMスクリプトを実行し、ファイル入出力でデータを交換します
    
    Args:
        script_path: FreeFEMスクリプトのパス
        input_array: 入力配列（オプション）
        output_file: 出力ファイルのパス
        
    Returns:
        成功フラグ、出力配列、標準出力、標準エラー出力
    """
    # 入力データがあれば、ファイルに書き込む
    if input_array is not None:
        np.savetxt('input.txt', input_array)
        print(f"入力データをファイルに書き込みました: input.txt")
    
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
        return False, None, stdout, stderr
    
    # 出力ファイルが存在するか確認
    if os.path.exists(output_file):
        try:
            # 出力ファイルを読み込む
            output_array = np.loadtxt(output_file)
            print(f"出力ファイルを読み込みました: {output_file}")
            print(f"出力配列の形状: {output_array.shape}")
            return True, output_array, stdout, stderr
        except Exception as e:
            print(f"出力ファイルの読み込みに失敗しました: {e}")
            return False, None, stdout, stderr
    else:
        print(f"出力ファイルが見つかりません: {output_file}")
        return False, None, stdout, stderr

def plot_freefem_solution(solution_array, mesh_size=10):
    """
    FreeFEMの解をプロットします
    
    Args:
        solution_array: FreeFEMから取得した解の配列
        mesh_size: メッシュのサイズ（デフォルト: 10）
    """
    # 2D表示用にデータを整形
    n = mesh_size + 1  # グリッドサイズ
    
    # 1次元配列をn×nの2次元配列に変換
    solution_2d = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            index = i * n + j
            if index < len(solution_array):
                solution_2d[i, j] = solution_array[index]
    
    # プロット
    plt.figure(figsize=(10, 8))
    
    # カラーマップでプロット
    plt.subplot(121)
    plt.pcolormesh(np.arange(n), np.arange(n), solution_2d, cmap='viridis', shading='auto')
    plt.colorbar(label='u value')
    plt.title('Poisson Equation Solution (2D)')
    plt.xlabel('x coordinate')
    plt.ylabel('y coordinate')
    
    # 3Dサーフェイスプロット
    ax = plt.subplot(122, projection='3d')
    x = np.linspace(0, 1, n)
    y = np.linspace(0, 1, n)
    X, Y = np.meshgrid(x, y)
    ax.plot_surface(X, Y, solution_2d, cmap='viridis', edgecolor='none')
    ax.set_title('Poisson Equation Solution (3D)')
    ax.set_xlabel('x coordinate')
    ax.set_ylabel('y coordinate')
    ax.set_zlabel('u value')
    
    plt.tight_layout()
    plt.savefig('poisson_solution.png')
    print("解のプロットを保存しました: poisson_solution.png")
    
    # 表示（GUIが利用可能な場合）
    try:
        plt.show()
    except Exception as e:
        print(f"プロットの表示に失敗しました（ファイルとして保存されています）: {e}")

def main():
    print("FreeFEMとファイル入出力でポアソン方程式を解くテストを実行します")
    
    # FreeFEMスクリプトのパス
    script_path = 'file_io_test.edp'
    
    # FreeFEMを実行
    success, solution, stdout, stderr = run_freefem_with_file_io(script_path)
    
    if success and solution is not None:
        print("FreeFEMからの解の取得に成功しました")
        print(f"解の要素数: {len(solution)}")
        print(f"解の最小値: {solution.min()}")
        print(f"解の最大値: {solution.max()}")
        
        # 解をプロット
        try:
            plot_freefem_solution(solution)
        except Exception as e:
            print(f"プロットの作成に失敗しました: {e}")
    else:
        print("FreeFEMスクリプトの実行に失敗しました")

if __name__ == "__main__":
    main() 