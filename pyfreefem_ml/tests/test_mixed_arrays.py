#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_mixed_arrays.py
複数の異なる型の配列を同時に処理するテスト
"""

import os
import sys
import numpy as np
import unittest
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# テスト対象モジュールをインポート
from pyfreefem_ml.freefem_interface import FreeFEMInterface

class TestMixedArrayCommunication(unittest.TestCase):
    """異なる型の配列の組み合わせテスト"""
    
    def setUp(self):
        """テスト準備"""
        self.debug = True
        # テスト用のFreeFEMインターフェースを作成
        self.ff = FreeFEMInterface(debug=self.debug)
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'ff'):
            self.ff.cleanup()
    
    def test_write_read_mixed_arrays(self):
        """Pythonで異なる型の配列を書き込み、読み込みテスト"""
        # テスト用の整数配列と浮動小数点配列を作成
        int_array = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        double_array = np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_int_array(int_array, "test_int_array")
        self.ff.write_double_array(double_array, "test_double_array")
        
        # 共有メモリから読み込み
        result_int_array = self.ff.read_int_array("test_int_array")
        result_double_array = self.ff.read_double_array("test_double_array")
        
        # 結果を検証
        np.testing.assert_array_equal(result_int_array, int_array,
                                     err_msg="読み込んだ整数配列が書き込んだ配列と一致しません")
        np.testing.assert_allclose(result_double_array, double_array, rtol=1e-10, atol=1e-10,
                                 err_msg="読み込んだ浮動小数点配列が書き込んだ配列と一致しません")
        
        print(f"テスト成功: 異なる型の配列を同時に処理できました")
    
    def test_freefem_mixed_array_processing(self):
        """FreeFEM側での異なる型の配列処理テスト"""
        # テスト用の配列
        int_array = np.array([10, 20, 30, 40, 50], dtype=np.int32)
        double_array = np.array([10.5, 20.5, 30.5, 40.5, 50.5], dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_int_array(int_array, "input_int_array")
        self.ff.write_double_array(double_array, "input_double_array")
        
        # FreeFEMスクリプトで処理
        script = """
        // 異なる型の配列処理テスト
        load "mmap-semaphore"
        
        // 配列を宣言
        int[int] input_int(5);
        real[int] input_double(5);
        int[int] output_int(5);
        real[int] output_double(5);
        
        // 共有メモリから読み込み
        ShmReadIntArray("input_int_array", input_int, ArrayInfo(5, 0));
        ShmReadDoubleArray("input_double_array", input_double, ArrayInfo(5, 0));
        
        // 計算処理（整数は+10、浮動小数点は*2）
        for (int i = 0; i < 5; i++) {
            output_int[i] = input_int[i] + 10;
            output_double[i] = input_double[i] * 2.0;
        }
        
        // 結果を共有メモリに書き込み
        ShmWriteIntArray("output_int_array", output_int, ArrayInfo(5, 0));
        ShmWriteDoubleArray("output_double_array", output_double, ArrayInfo(5, 0));
        """
        
        # スクリプトを実行
        success, stdout, stderr = self.ff.run_inline_script(script)
        self.assertTrue(success, f"FreeFEMスクリプト実行エラー: {stderr}")
        
        # 結果を読み込み
        result_int_array = self.ff.read_int_array("output_int_array")
        result_double_array = self.ff.read_double_array("output_double_array")
        
        # 期待される結果
        expected_int_array = int_array + 10
        expected_double_array = double_array * 2.0
        
        # 結果を検証
        np.testing.assert_array_equal(result_int_array, expected_int_array,
                                     err_msg="FreeFEMでの整数配列処理結果が期待値と一致しません")
        np.testing.assert_allclose(result_double_array, expected_double_array, rtol=1e-10, atol=1e-10,
                                 err_msg="FreeFEMでの浮動小数点配列処理結果が期待値と一致しません")
        
        print(f"テスト成功: FreeFEMでの異なる型の配列処理が正常に完了しました")
    
    def test_cross_conversion(self):
        """異なる型の配列間の変換テスト"""
        # 浮動小数点配列から整数配列への変換
        double_array = np.array([1.1, 2.9, 3.5, 4.2, 5.8], dtype=np.float64)
        
        # 共有メモリに浮動小数点配列として書き込み
        self.ff.write_double_array(double_array, "double_to_int_array")
        
        # FreeFEMスクリプトで変換処理
        script = """
        // 型変換テスト
        load "mmap-semaphore"
        
        // 配列を宣言
        real[int] double_array(5);
        int[int] int_array(5);
        
        // 浮動小数点配列を読み込み
        ShmReadDoubleArray("double_to_int_array", double_array, ArrayInfo(5, 0));
        
        // 整数に変換（切り捨て）
        for (int i = 0; i < 5; i++) {
            int_array[i] = int(double_array[i]);
        }
        
        // 整数配列として書き込み
        ShmWriteIntArray("converted_int_array", int_array, ArrayInfo(5, 0));
        """
        
        # スクリプトを実行
        success, stdout, stderr = self.ff.run_inline_script(script)
        self.assertTrue(success, f"FreeFEMスクリプト実行エラー: {stderr}")
        
        # 結果を読み込み
        result_int_array = self.ff.read_int_array("converted_int_array")
        
        # 期待される結果（浮動小数点から整数への変換は切り捨て）
        expected_int_array = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        
        # 結果を検証
        np.testing.assert_array_equal(result_int_array, expected_int_array,
                                     err_msg="型変換結果が期待値と一致しません")
        
        print(f"テスト成功: 浮動小数点配列から整数配列への変換が正常に完了しました")
    
    def test_multiple_dimension_array(self):
        """2次元配列の処理テスト"""
        # 2D配列を作成（行列）
        rows, cols = 3, 4
        
        # 整数2D配列
        int_matrix = np.arange(rows * cols).reshape(rows, cols).astype(np.int32)
        
        # 浮動小数点2D配列
        double_matrix = (np.arange(rows * cols) * 1.5).reshape(rows, cols).astype(np.float64)
        
        # フラット化して共有メモリに書き込み
        self.ff.write_int_array(int_matrix.flatten(), "int_matrix", shape=[rows, cols])
        self.ff.write_double_array(double_matrix.flatten(), "double_matrix", shape=[rows, cols])
        
        # FreeFEMスクリプトで処理
        script = f"""
        // 2次元配列処理テスト
        load "mmap-semaphore"
        
        // 配列サイズ
        int rows = {rows};
        int cols = {cols};
        int total = rows * cols;
        
        // フラット配列として宣言
        int[int] int_flat(total);
        real[int] double_flat(total);
        int[int] out_int_flat(total);
        real[int] out_double_flat(total);
        
        // 共有メモリから読み込み
        ShmReadIntArray("int_matrix", int_flat, ArrayInfo(total, 0));
        ShmReadDoubleArray("double_matrix", double_flat, ArrayInfo(total, 0));
        
        // 行列の要素ごとに処理（転置として計算）
        for (int i = 0; i < rows; i++) {{
            for (int j = 0; j < cols; j++) {{
                // 元の行列のインデックス（行優先）
                int src_idx = i * cols + j;
                // 転置行列のインデックス
                int dst_idx = j * rows + i;
                
                // 転置して値をコピー
                out_int_flat[dst_idx] = int_flat[src_idx];
                out_double_flat[dst_idx] = double_flat[src_idx];
            }}
        }}
        
        // 結果を共有メモリに書き込み
        ShmWriteIntArray("transposed_int_matrix", out_int_flat, ArrayInfo(total, 0));
        ShmWriteDoubleArray("transposed_double_matrix", out_double_flat, ArrayInfo(total, 0));
        """
        
        # スクリプトを実行
        success, stdout, stderr = self.ff.run_inline_script(script)
        self.assertTrue(success, f"FreeFEMスクリプト実行エラー: {stderr}")
        
        # 結果を読み込み
        result_int_flat = self.ff.read_int_array("transposed_int_matrix")
        result_double_flat = self.ff.read_double_array("transposed_double_matrix")
        
        # 元の次元に戻す
        result_int_matrix = result_int_flat.reshape(cols, rows)  # 転置後のサイズ
        result_double_matrix = result_double_flat.reshape(cols, rows)  # 転置後のサイズ
        
        # 期待される結果（転置行列）
        expected_int_matrix = int_matrix.T
        expected_double_matrix = double_matrix.T
        
        # 結果を検証
        np.testing.assert_array_equal(result_int_matrix, expected_int_matrix,
                                     err_msg="整数行列の転置結果が期待値と一致しません")
        np.testing.assert_allclose(result_double_matrix, expected_double_matrix, rtol=1e-10, atol=1e-10,
                                 err_msg="浮動小数点行列の転置結果が期待値と一致しません")
        
        print(f"テスト成功: 2次元配列の処理が正常に完了しました")
        
def run_tests():
    """テストを実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMixedArrayCommunication)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 