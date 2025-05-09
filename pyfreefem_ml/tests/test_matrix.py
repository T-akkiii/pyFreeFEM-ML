#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_matrix.py
行列（2次元配列）通信のテスト用Pythonスクリプト

このスクリプトでは、FreeFEMと行列データを共有メモリを介して
送受信する機能をテストします。
"""

import os
import sys
import time
import unittest
import logging
import numpy as np
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# PyFreeFEMライブラリをインポート
from pyfreefem_ml.freefem_interface import FreeFEMInterface
from pyfreefem_ml.utils import is_wsl

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_matrix.log')
    ]
)
logger = logging.getLogger(__name__)

class TestMatrixCommunication(unittest.TestCase):
    """行列通信のテストケース"""
    
    def setUp(self):
        """テスト前の準備"""
        self.debug = True
        # WSL環境かどうかを自動検出
        self.wsl_mode = is_wsl()
        logger.info(f"環境: {'WSL' if self.wsl_mode else '通常'}")
        logger.info("テスト開始")
        
        # FreeFEMインターフェースを初期化
        self.ff = FreeFEMInterface(debug=self.debug, wsl_mode=self.wsl_mode)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'ff'):
            self.ff.cleanup()
        logger.info("テスト終了")
    
    def test_small_double_matrix(self):
        """小さな浮動小数点行列のテスト"""
        logger.info("小さな浮動小数点行列のテスト開始")
        
        # テスト用行列（3x3）
        matrix = np.array([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0]
        ], dtype=np.float64)
        
        # 行列を共有メモリに書き込み
        self.ff.write_matrix(matrix, "test_double_matrix")
        
        # FreeFEMスクリプトで行列を読み込み、転置して書き込み
        script = """
        load "mmap-semaphore"
        
        // 行列情報の取得
        real[int, int] matrix(3, 3);
        
        // 共有メモリから行列を読み込み
        int offset = 0;  // これはシリアライズされた配列のデータオフセット
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                offset = i * 3 + j;
                real val;
                ShmReadArrayElement("test_double_matrix", offset, val);
                matrix(i, j) = val;
            }
        }
        
        // 読み込んだ行列の表示
        cout << "FreeFEMで読み込んだ行列:" << endl;
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                cout << matrix(i, j) << " ";
            }
            cout << endl;
        }
        
        // 行列の転置
        real[int, int] transposed(3, 3);
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                transposed(i, j) = matrix(j, i);
            }
        }
        
        // 転置行列の表示
        cout << "転置行列:" << endl;
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                cout << transposed(i, j) << " ";
            }
            cout << endl;
        }
        
        // 転置行列をシリアライズして共有メモリに書き込み
        real[int] serialized(9);
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                serialized[i * 3 + j] = transposed(i, j);
            }
        }
        
        // 転置行列を共有メモリに書き込み
        ShmWriteArray("result_matrix", serialized, ArrayInfo(9, 0));
        
        cout << "転置行列を共有メモリに書き込みました" << endl;
        """
        
        # スクリプトを実行
        result = self.ff.run_inline_script(script)
        self.assertTrue(result[0], f"スクリプト実行エラー: {result[2]}")
        logger.info(f"スクリプト出力:\n{result[1]}")
        
        # 結果を読み込み
        result_array = self.ff.read_array("result_matrix")
        
        # 1次元配列から3x3行列に変換
        result_matrix = result_array.reshape(3, 3)
        
        # 期待される結果（元の行列の転置）と比較
        expected = matrix.T
        np.testing.assert_allclose(result_matrix, expected, rtol=1e-5)
        
        logger.info("小さな浮動小数点行列のテスト成功")
    
    def test_int_matrix(self):
        """整数行列のテスト"""
        logger.info("整数行列のテスト開始")
        
        # テスト用整数行列（2x4）
        int_matrix = np.array([
            [10, 20, 30, 40],
            [50, 60, 70, 80]
        ], dtype=np.int32)
        
        # 整数行列を共有メモリに書き込み
        self.ff.write_int_matrix(int_matrix, "test_int_matrix")
        
        # FreeFEMスクリプトで整数行列を読み込み、各要素に10を加算
        script = """
        load "mmap-semaphore"
        
        // 行列情報
        int rows = 2;
        int cols = 4;
        int[int, int] matrix(rows, cols);
        
        // 共有メモリから整数行列を読み込み
        int offset = 0;
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                offset = i * cols + j;
                int val;
                ShmReadIntArrayElement("test_int_matrix", offset, val);
                matrix(i, j) = val;
            }
        }
        
        // 読み込んだ行列の表示
        cout << "FreeFEMで読み込んだ整数行列:" << endl;
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                cout << matrix(i, j) << " ";
            }
            cout << endl;
        }
        
        // 各要素に10を加算
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                matrix(i, j) += 10;
            }
        }
        
        // 結果行列の表示
        cout << "加算後の行列:" << endl;
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                cout << matrix(i, j) << " ";
            }
            cout << endl;
        }
        
        // 結果をシリアライズして共有メモリに書き込み
        int[int] serialized(rows * cols);
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                serialized[i * cols + j] = matrix(i, j);
            }
        }
        
        // 結果を共有メモリに書き込み
        ShmWriteIntArray("result_int_matrix", serialized, ArrayInfo(rows * cols, 0));
        
        cout << "結果を共有メモリに書き込みました" << endl;
        """
        
        # スクリプトを実行
        result = self.ff.run_inline_script(script)
        self.assertTrue(result[0], f"スクリプト実行エラー: {result[2]}")
        logger.info(f"スクリプト出力:\n{result[1]}")
        
        # 結果を読み込み
        result_array = self.ff.read_int_array("result_int_matrix")
        
        # 1次元配列から2x4行列に変換
        result_matrix = result_array.reshape(2, 4)
        
        # 期待される結果（元の行列に10を加算）と比較
        expected = int_matrix + 10
        np.testing.assert_array_equal(result_matrix, expected)
        
        logger.info("整数行列のテスト成功")
    
    def test_large_matrix(self):
        """大きな行列のテスト"""
        logger.info("大きな行列のテスト開始")
        
        # テスト用の大きな行列（100x100）
        rows, cols = 100, 100
        large_matrix = np.random.random((rows, cols))
        
        # 行列を共有メモリに書き込み
        self.ff.write_matrix(large_matrix, "test_large_matrix")
        
        # FreeFEMスクリプトで行列の対角成分の合計（トレース）を計算
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
        result = self.ff.run_inline_script(script)
        self.assertTrue(result[0], f"スクリプト実行エラー: {result[2]}")
        logger.info(f"スクリプト出力:\n{result[1]}")
        
        # 結果を読み込み
        trace_result = self.ff.read_double("matrix_trace")
        
        # 期待される結果（対角成分の合計）と比較
        expected_trace = np.trace(large_matrix)
        self.assertAlmostEqual(trace_result, expected_trace, delta=1e-5)
        
        logger.info("大きな行列のテスト成功")
    
    def test_matrix_operations(self):
        """行列演算のテスト"""
        logger.info("行列演算のテスト開始")
        
        # テスト用行列A（2x3）
        matrix_a = np.array([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0]
        ], dtype=np.float64)
        
        # テスト用行列B（3x2）
        matrix_b = np.array([
            [7.0, 8.0],
            [9.0, 10.0],
            [11.0, 12.0]
        ], dtype=np.float64)
        
        # 行列を共有メモリに書き込み
        self.ff.write_matrix(matrix_a, "matrix_a")
        self.ff.write_matrix(matrix_b, "matrix_b")
        
        # FreeFEMスクリプトで行列の積を計算
        script = """
        load "mmap-semaphore"
        
        // 行列A情報
        int rows_a = 2;
        int cols_a = 3;
        real[int, int] matrix_a(rows_a, cols_a);
        
        // 行列Bの情報
        int rows_b = 3;
        int cols_b = 2;
        real[int, int] matrix_b(rows_b, cols_b);
        
        // 共有メモリから行列Aを読み込み
        for (int i = 0; i < rows_a; i++) {
            for (int j = 0; j < cols_a; j++) {
                int offset = i * cols_a + j;
                real val;
                ShmReadArrayElement("matrix_a", offset, val);
                matrix_a(i, j) = val;
            }
        }
        
        // 共有メモリから行列Bを読み込み
        for (int i = 0; i < rows_b; i++) {
            for (int j = 0; j < cols_b; j++) {
                int offset = i * cols_b + j;
                real val;
                ShmReadArrayElement("matrix_b", offset, val);
                matrix_b(i, j) = val;
            }
        }
        
        // 行列の積C = A×Bを計算
        real[int, int] matrix_c(rows_a, cols_b);
        
        for (int i = 0; i < rows_a; i++) {
            for (int j = 0; j < cols_b; j++) {
                matrix_c(i, j) = 0.0;
                for (int k = 0; k < cols_a; k++) {
                    matrix_c(i, j) += matrix_a(i, k) * matrix_b(k, j);
                }
            }
        }
        
        // 結果行列の表示
        cout << "行列積 C = A×B:" << endl;
        for (int i = 0; i < rows_a; i++) {
            for (int j = 0; j < cols_b; j++) {
                cout << matrix_c(i, j) << " ";
            }
            cout << endl;
        }
        
        // 結果をシリアライズして共有メモリに書き込み
        real[int] serialized(rows_a * cols_b);
        for (int i = 0; i < rows_a; i++) {
            for (int j = 0; j < cols_b; j++) {
                serialized[i * cols_b + j] = matrix_c(i, j);
            }
        }
        
        // 結果を共有メモリに書き込み
        ShmWriteArray("matrix_c", serialized, ArrayInfo(rows_a * cols_b, 0));
        
        cout << "結果行列を共有メモリに書き込みました" << endl;
        """
        
        # スクリプトを実行
        result = self.ff.run_inline_script(script)
        self.assertTrue(result[0], f"スクリプト実行エラー: {result[2]}")
        logger.info(f"スクリプト出力:\n{result[1]}")
        
        # 結果を読み込み
        result_array = self.ff.read_array("matrix_c")
        
        # 1次元配列から2x2行列に変換
        result_matrix = result_array.reshape(2, 2)
        
        # 期待される結果（NumPyで計算した行列積）と比較
        expected = np.matmul(matrix_a, matrix_b)
        np.testing.assert_allclose(result_matrix, expected, rtol=1e-5)
        
        logger.info("行列演算のテスト成功")

def run_tests():
    """テストスイートを実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMatrixCommunication)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 