#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_pyfreefem.py
PyFreeFEMライブラリのテスト用Pythonスクリプト
"""

import os
import sys
import time
import numpy as np
import unittest
import logging
from pathlib import Path

# プロジェクトルートをパスに追加して、モジュールをインポートできるようにする
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# PyFreeFEMライブラリをインポート
from pyfreefem_ml.freefem_interface import FreeFEMInterface
from pyfreefem_ml.errors import FreeFEMBaseError

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_pyfreefem.log')
    ]
)
logger = logging.getLogger(__name__)

class TestPyFreeFEM(unittest.TestCase):
    """PyFreeFEMライブラリのテストケース"""
    
    def setUp(self):
        """テスト前の準備"""
        self.debug = True
        logger.info("テスト開始")
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        logger.info("テスト終了")
    
    def test_basic_data_types(self):
        """基本データ型の読み書きをテスト"""
        ff = FreeFEMInterface(debug=self.debug)
        
        # 整数値の書き込みと読み込み
        ff.write_int(42, "test_int")
        int_value = ff.read_int("test_int")
        self.assertEqual(int_value, 42)
        
        # 浮動小数点値の書き込みと読み込み
        ff.write_double(3.14159, "test_double")
        double_value = ff.read_double("test_double")
        self.assertAlmostEqual(double_value, 3.14159)
        
        # 文字列の書き込みと読み込み
        ff.write_string("Hello PyFreeFEM", "test_string")
        string_value = ff.read_string("test_string")
        self.assertEqual(string_value, "Hello PyFreeFEM")
        
        # リソースの解放
        ff.cleanup()
    
    def test_double_array_read_write(self):
        """double配列の書き込みと読み込みをテスト"""
        ff = FreeFEMInterface(debug=self.debug)
        
        # テスト用配列
        array = np.array([1.0, 2.5, 3.14, -5.0, 0.0], dtype=np.float64)
        
        # 配列を共有メモリに書き込み
        ff.write_array(array, "test_double_array")
        
        # FreeFEMスクリプトで読み込みと書き込みを実行
        result = ff.run_inline_script("""
            load "mmap-semaphore"
            real[int] arr(5);
            
            // 共有メモリから配列を読み込み
            ShmReadArray("test_double_array", arr, ArrayInfo(5, 0));
            
            // 各要素を2倍して書き込み
            for (int i = 0; i < 5; i++)
                arr[i] = arr[i] * 2;
            
            // 結果を共有メモリに書き込み
            ShmWriteArray("result_double_array", arr, ArrayInfo(5, 0));
        """)
        
        # 結果の確認
        self.assertTrue(result[0], f"スクリプト実行エラー: {result[2]}")
        
        # 共有メモリから結果を読み込み
        result_array = ff.read_array("result_double_array")
        
        # 期待される結果と比較
        expected = array * 2
        np.testing.assert_allclose(result_array, expected, rtol=1e-5)
        
        # リソースの解放
        ff.cleanup()
    
    def test_int_array_read_write(self):
        """int配列の書き込みと読み込みをテスト"""
        ff = FreeFEMInterface(debug=self.debug)
        
        # テスト用整数配列
        int_array = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        
        # 整数配列を共有メモリに書き込み
        ff.write_int_array(int_array, "test_int_array")
        
        # FreeFEMスクリプトで読み込みと書き込みを実行
        result = ff.run_inline_script("""
            load "mmap-semaphore"
            int[int] arr(5);
            
            // 共有メモリから整数配列を読み込み
            ShmReadIntArray("test_int_array", arr, ArrayInfo(5, 0));
            
            // 各要素に10を加算して書き込み
            for (int i = 0; i < 5; i++)
                arr[i] = arr[i] + 10;
            
            // 結果を共有メモリに書き込み
            ShmWriteIntArray("result_int_array", arr, ArrayInfo(5, 0));
        """)
        
        # 結果の確認
        self.assertTrue(result[0], f"スクリプト実行エラー: {result[2]}")
        
        # 共有メモリから結果を読み込み
        result_array = ff.read_int_array("result_int_array")
        
        # 期待される結果と比較
        expected = int_array + 10
        np.testing.assert_array_equal(result_array, expected)
        
        # リソースの解放
        ff.cleanup()
    
    def test_mixed_array_types(self):
        """異なる型の配列の相互変換をテスト"""
        ff = FreeFEMInterface(debug=self.debug)
        
        # 浮動小数点配列をint配列として書き込み
        float_array = np.array([1.5, 2.7, 3.2, 4.9, 5.1])
        ff.write_int_array(float_array, "mixed_array_float_to_int")
        
        # 整数配列を浮動小数点配列として読み込み
        int_array = np.array([10, 20, 30, 40, 50], dtype=np.int32)
        ff.write_int_array(int_array, "mixed_array_int")
        result_float = ff.read_array("mixed_array_int")
        
        # 結果の確認
        expected_int = np.array([1, 2, 3, 4, 5], dtype=np.int32)  # 小数点以下は切り捨て
        result_int = ff.read_int_array("mixed_array_float_to_int")
        np.testing.assert_array_equal(result_int, expected_int)
        
        expected_float = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        np.testing.assert_allclose(result_float, expected_float)
        
        # リソースの解放
        ff.cleanup()

def run_tests():
    """テストスイートを実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPyFreeFEM)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 