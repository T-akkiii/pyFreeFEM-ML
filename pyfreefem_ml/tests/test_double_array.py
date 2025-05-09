#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_double_array.py
浮動小数点配列の共有メモリ通信機能のテスト
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

class TestDoubleArrayCommunication(unittest.TestCase):
    """浮動小数点配列の通信テストケース"""
    
    def setUp(self):
        """テスト準備"""
        self.debug = True
        # テスト用のFreeFEMインターフェースを作成
        self.ff = FreeFEMInterface(debug=self.debug)
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'ff'):
            self.ff.cleanup()
    
    def test_write_read_double_array(self):
        """Pythonで浮動小数点配列を書き込み、読み込みテスト"""
        # テスト用の浮動小数点配列を作成
        test_array = np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_double_array(test_array, "test_double_array")
        
        # 共有メモリから読み込み
        result_array = self.ff.read_double_array("test_double_array")
        
        # 結果を検証（浮動小数点のため許容誤差あり）
        np.testing.assert_allclose(result_array, test_array, rtol=1e-10, atol=1e-10,
                                  err_msg="読み込んだ配列が書き込んだ配列と一致しません")
        
        print(f"テスト成功: 浮動小数点配列 {test_array} を書き込み、正常に読み込みました")
    
    def test_freefem_double_array_processing(self):
        """FreeFEM側での浮動小数点配列処理テスト"""
        # テスト用の浮動小数点配列
        test_array = np.array([10.5, 20.5, 30.5, 40.5, 50.5], dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_double_array(test_array, "input_double_array")
        
        # FreeFEMスクリプトで処理
        script = """
        // 浮動小数点配列処理テスト
        load "mmap-semaphore"
        
        // 配列を宣言
        real[int] input(5);
        real[int] output(5);
        
        // 共有メモリから読み込み
        ShmReadDoubleArray("input_double_array", input, ArrayInfo(5, 0));
        
        // 各要素を2倍
        for (int i = 0; i < 5; i++) {
            output[i] = input[i] * 2.0;
        }
        
        // 結果を共有メモリに書き込み
        ShmWriteDoubleArray("output_double_array", output, ArrayInfo(5, 0));
        """
        
        # スクリプトを実行
        success, stdout, stderr = self.ff.run_inline_script(script)
        self.assertTrue(success, f"FreeFEMスクリプト実行エラー: {stderr}")
        
        # 結果を読み込み
        result_array = self.ff.read_double_array("output_double_array")
        
        # 期待される結果: 各要素を2倍
        expected_array = test_array * 2.0
        
        # 結果を検証
        np.testing.assert_allclose(result_array, expected_array, rtol=1e-10, atol=1e-10,
                                  err_msg="FreeFEMでの処理結果が期待値と一致しません")
        
        print(f"テスト成功: FreeFEMでの浮動小数点配列処理が正常に完了しました")
    
    def test_large_double_array(self):
        """大規模浮動小数点配列のテスト"""
        # 大きめの浮動小数点配列を作成
        size = 1000
        test_array = np.linspace(0.0, 100.0, size, dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_double_array(test_array, "large_double_array")
        
        # 共有メモリから読み込み
        result_array = self.ff.read_double_array("large_double_array")
        
        # 結果を検証
        np.testing.assert_allclose(result_array, test_array, rtol=1e-10, atol=1e-10,
                                  err_msg="大規模配列の読み書きに問題があります")
        
        print(f"テスト成功: {size}要素の浮動小数点配列を正常に処理しました")
    
    def test_precision(self):
        """浮動小数点の精度テスト"""
        # 精度テスト用の配列（小さな値と大きな値を混在）
        test_array = np.array([1e-10, 1e-5, 1.0, 1e5, 1e10], dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_double_array(test_array, "precision_test_array")
        
        # 共有メモリから読み込み
        result_array = self.ff.read_double_array("precision_test_array")
        
        # 結果を検証（相対誤差でチェック）
        np.testing.assert_allclose(result_array, test_array, rtol=1e-14, atol=0,
                                  err_msg="浮動小数点の精度が保持されていません")
        
        # 絶対値の小さな値で特に検証
        small_value_index = 0  # 1e-10の位置
        relative_error = abs((result_array[small_value_index] - test_array[small_value_index]) 
                             / test_array[small_value_index])
        self.assertLess(relative_error, 1e-14, 
                        f"小さな値の精度が不十分です: 相対誤差 = {relative_error}")
        
        print(f"テスト成功: 浮動小数点の精度が正常に保持されました")
    
    def test_scientific_notation(self):
        """科学的表記法の値のテスト"""
        # 科学的表記法で表される値の配列
        test_array = np.array([6.02214076e23,  # アボガドロ数
                               1.602176634e-19,  # 電気素量
                               2.99792458e8,  # 光速
                               6.62607015e-34,  # プランク定数
                               1.38064852e-23], # ボルツマン定数
                             dtype=np.float64)
        
        # 共有メモリに書き込み
        self.ff.write_double_array(test_array, "scientific_array")
        
        # 共有メモリから読み込み
        result_array = self.ff.read_double_array("scientific_array")
        
        # 結果を検証
        np.testing.assert_allclose(result_array, test_array, rtol=1e-14, atol=0,
                                  err_msg="科学的表記法の値が正しく処理されていません")
        
        print(f"テスト成功: 科学的表記法の値が正常に処理されました")

def run_tests():
    """テストを実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDoubleArrayCommunication)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 