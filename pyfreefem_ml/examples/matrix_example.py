#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
行列処理のFreeFEMとPython間の連携例

このスクリプトでは、NumPy行列をFreeFEMと共有して、
行列演算を実行する方法を示します。
"""

import sys
import os
import numpy as np
import logging
from time import time

# パスを追加して親ディレクトリのモジュールをインポートできるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyfreefem_mlモジュールをインポート
from pyfreefem_ml import FreeFEMInterface

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('matrix_example')

def small_matrix_example(ff):
    """小さな行列の例（転置操作）"""
    logger.info("==== 小さな行列の例（転置操作）====")
    
    # 2x3行列を作成
    matrix = np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0]
    ], dtype=np.float64)
    
    logger.info(f"元の行列:\n{matrix}")
    
    # 行列を共有メモリに書き込み
    ff.write_matrix(matrix, "test_matrix")
    
    # FreeFEMスクリプトで行列を転置
    script = """
    load "mmap-semaphore"
    
    // 行列情報
    int rows = 2;
    int cols = 3;
    
    // 行列の読み込み
    real[int, int] matrix(rows, cols);
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            real val;
            int offset = i * cols + j;
            ShmReadArrayElement("test_matrix", offset, val);
            matrix(i, j) = val;
            cout << "matrix(" << i << "," << j << ") = " << val << endl;
        }
    }
    
    // 転置行列の作成
    real[int, int] transposed(cols, rows);
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            transposed(j, i) = matrix(i, j);
        }
    }
    
    // 転置行列の表示
    cout << "転置行列:" << endl;
    for (int i = 0; i < cols; i++) {
        for (int j = 0; j < rows; j++) {
            cout << transposed(i, j) << " ";
        }
        cout << endl;
    }
    
    // 転置行列を共有メモリに書き込み
    real[int] serialized(cols * rows);
    for (int i = 0; i < cols; i++) {
        for (int j = 0; j < rows; j++) {
            serialized[i * rows + j] = transposed(i, j);
        }
    }
    
    ShmWriteArray("transposed_matrix", serialized, ArrayInfo(cols * rows, 0));
    
    cout << "転置行列を共有メモリに書き込みました" << endl;
    """
    
    # スクリプトを実行
    result = ff.run_inline_script(script)
    if not result[0]:
        logger.error(f"スクリプト実行エラー: {result[2]}")
        return False
    
    logger.info(f"スクリプト出力:\n{result[1]}")
    
    # 転置行列を読み込み
    transposed_array = ff.read_array("transposed_matrix")
    transposed_matrix = transposed_array.reshape(3, 2)  # 3x2に変形
    
    logger.info(f"Python側で受け取った転置行列:\n{transposed_matrix}")
    
    # NumPyの転置と比較
    numpy_transposed = matrix.T
    logger.info(f"NumPyの転置:\n{numpy_transposed}")
    
    # 結果の検証
    if np.allclose(transposed_matrix, numpy_transposed):
        logger.info("転置操作の検証成功 ✓")
        return True
    else:
        logger.error("転置操作の検証失敗 ✗")
        return False

def matrix_multiplication_example(ff):
    """行列積の例"""
    logger.info("==== 行列積の例 ====")
    
    # 行列Aを作成 (2x3)
    matrix_a = np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0]
    ], dtype=np.float64)
    
    # 行列Bを作成 (3x2)
    matrix_b = np.array([
        [7.0, 8.0],
        [9.0, 10.0],
        [11.0, 12.0]
    ], dtype=np.float64)
    
    logger.info(f"行列A:\n{matrix_a}")
    logger.info(f"行列B:\n{matrix_b}")
    
    # 行列をFreeFEMと共有
    ff.write_matrix(matrix_a, "matrix_a")
    ff.write_matrix(matrix_b, "matrix_b")
    
    # FreeFEMスクリプトで行列の積を計算
    script = """
    load "mmap-semaphore"
    
    // 行列情報
    int rows_a = 2;
    int cols_a = 3;
    int rows_b = 3;
    int cols_b = 2;
    
    // 結果行列のサイズ
    int rows_c = rows_a;
    int cols_c = cols_b;
    
    // 共有メモリから行列を読み込み
    real[int, int] matrix_a(rows_a, cols_a);
    real[int, int] matrix_b(rows_b, cols_b);
    
    // 行列Aの読み込み
    for (int i = 0; i < rows_a; i++) {
        for (int j = 0; j < cols_a; j++) {
            real val;
            ShmReadArrayElement("matrix_a", i * cols_a + j, val);
            matrix_a(i, j) = val;
        }
    }
    
    // 行列Bの読み込み
    for (int i = 0; i < rows_b; i++) {
        for (int j = 0; j < cols_b; j++) {
            real val;
            ShmReadArrayElement("matrix_b", i * cols_b + j, val);
            matrix_b(i, j) = val;
        }
    }
    
    // 行列積の計算 C = A * B
    real[int, int] matrix_c(rows_c, cols_c);
    
    for (int i = 0; i < rows_c; i++) {
        for (int j = 0; j < cols_c; j++) {
            matrix_c(i, j) = 0.0;
            // 行列積の計算
            for (int k = 0; k < cols_a; k++) {
                matrix_c(i, j) += matrix_a(i, k) * matrix_b(k, j);
            }
        }
    }
    
    // 結果行列の表示
    cout << "行列C (A×B):" << endl;
    for (int i = 0; i < rows_c; i++) {
        for (int j = 0; j < cols_c; j++) {
            cout << matrix_c(i, j) << " ";
        }
        cout << endl;
    }
    
    // 結果を共有メモリに書き込み
    real[int] serialized(rows_c * cols_c);
    for (int i = 0; i < rows_c; i++) {
        for (int j = 0; j < cols_c; j++) {
            serialized[i * cols_c + j] = matrix_c(i, j);
        }
    }
    
    ShmWriteArray("matrix_c", serialized, ArrayInfo(rows_c * cols_c, 0));
    cout << "結果行列を共有メモリに書き込みました" << endl;
    """
    
    # スクリプトを実行
    result = ff.run_inline_script(script)
    if not result[0]:
        logger.error(f"スクリプト実行エラー: {result[2]}")
        return False
    
    logger.info(f"スクリプト出力:\n{result[1]}")
    
    # 結果行列を読み込み
    result_array = ff.read_array("matrix_c")
    result_matrix = result_array.reshape(2, 2)  # 2x2結果行列
    
    logger.info(f"Python側で受け取った結果行列:\n{result_matrix}")
    
    # NumPyの行列積と比較
    numpy_result = np.matmul(matrix_a, matrix_b)
    logger.info(f"NumPyの行列積:\n{numpy_result}")
    
    # 結果の検証
    if np.allclose(result_matrix, numpy_result):
        logger.info("行列積の検証成功 ✓")
        return True
    else:
        logger.error("行列積の検証失敗 ✗")
        return False

def large_matrix_example(ff):
    """大きな行列のトレース計算例"""
    logger.info("==== 大きな行列のトレース計算例 ====")
    
    # 100x100のランダム行列を作成
    size = 100
    large_matrix = np.random.rand(size, size)
    
    # NumPyでトレースを計算（比較用）
    numpy_trace = np.trace(large_matrix)
    logger.info(f"NumPyで計算したトレース: {numpy_trace}")
    
    # 行列を共有メモリに書き込み
    ff.write_matrix(large_matrix, "test_large_matrix")
    logger.info(f"大きな行列({size}x{size})を共有メモリに書き込みました")
    
    # FreeFEMスクリプトでトレースを計算
    script = """
    load "mmap-semaphore"
    
    // 行列情報
    int rows = 100;
    int cols = 100;
    
    // トレースを計算（対角成分の合計）
    real trace = 0.0;
    for (int i = 0; i < rows; i++) {
        real diagonal_element;
        int offset = i * cols + i;  // 対角成分のインデックス
        ShmReadArrayElement("test_large_matrix", offset, diagonal_element);
        trace += diagonal_element;
    }
    
    cout << "行列のトレース: " << trace << endl;
    
    // トレースを共有メモリに書き込み
    ShmWriteDouble("matrix_trace", 0, trace);
    cout << "トレースを共有メモリに書き込みました" << endl;
    """
    
    # スクリプトを実行
    start_time = time()
    result = ff.run_inline_script(script)
    end_time = time()
    if not result[0]:
        logger.error(f"スクリプト実行エラー: {result[2]}")
        return False
    
    logger.info(f"FreeFEMでの計算時間: {end_time - start_time:.4f}秒")
    logger.info(f"スクリプト出力:\n{result[1]}")
    
    # トレースを読み込み
    trace_result = ff.read_double("matrix_trace")
    logger.info(f"Python側で受け取ったトレース: {trace_result}")
    
    # 結果の検証
    if abs(trace_result - numpy_trace) < 1e-5:
        logger.info("トレース計算の検証成功 ✓")
        return True
    else:
        logger.error(f"トレース計算の検証失敗 ✗ (差: {abs(trace_result - numpy_trace)})")
        return False

def main():
    """メイン関数"""
    logger.info("行列処理の例を開始")
    
    # FreeFEMインターフェースを初期化
    ff = FreeFEMInterface(debug=True)
    
    # 例1: 小さな行列の転置
    success = small_matrix_example(ff)
    if not success:
        logger.error("小さな行列の例が失敗しました")
    
    # 例2: 行列の積
    success = matrix_multiplication_example(ff)
    if not success:
        logger.error("行列積の例が失敗しました")
    
    # 例3: 大きな行列のトレース
    success = large_matrix_example(ff)
    if not success:
        logger.error("大きな行列の例が失敗しました")
    
    logger.info("行列処理の例を終了")

if __name__ == "__main__":
    main() 