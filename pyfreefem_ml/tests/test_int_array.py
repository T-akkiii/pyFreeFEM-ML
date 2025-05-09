#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_int_array.py
整数配列の共有メモリ通信機能のテスト
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

class TestIntArrayCommunication(unittest.TestCase):
    """整数配列の通信テストケース"""
    
    def setUp(self):
        """テスト準備"""
        self.debug = True
        # テスト用のFreeFEMインターフェースを作成
        self.ff = FreeFEMInterface(debug=self.debug)
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'ff'):
            self.ff.cleanup()
    
    def test_write_read_int_array(self):
        """Pythonで整数配列を書き込み、読み込みテスト"""
        # テスト用の整数配列を作成
        test_array = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        
        # 共有メモリに書き込み
        self.ff.write_int_array(test_array, "test_int_array")
        
        # 共有メモリから読み込み
        result_array = self.ff.read_int_array("test_int_array")
        
        # 結果を検証
        np.testing.assert_array_equal(result_array, test_array,
                                     "読み込んだ配列が書き込んだ配列と一致しません")
        
        print(f"テスト成功: 整数配列 {test_array} を書き込み、正常に読み込みました")
    
    def test_freefem_int_array_processing(self):
        """FreeFEM側での整数配列処理テスト"""
        # テスト用の整数配列
        test_array = np.array([10, 20, 30, 40, 50], dtype=np.int32)
        
        # 共有メモリに書き込み
        self.ff.write_int_array(test_array, "input_int_array")
        
        # FreeFEMスクリプトで処理
        script = """
        // 整数配列処理テスト
        load "mmap-semaphore"
        
        // 整数配列を宣言
        int[int] input(5);
        int[int] output(5);
        
        // 共有メモリから読み込み
        ShmReadIntArray("input_int_array", input, ArrayInfo(5, 0));
        
        // 各要素に10を加算
        for (int i = 0; i < 5; i++) {
            output[i] = input[i] + 10;
        }
        
        // 結果を共有メモリに書き込み
        ShmWriteIntArray("output_int_array", output, ArrayInfo(5, 0));
        """
        
        # スクリプトを実行
        success, stdout, stderr = self.ff.run_inline_script(script)
        self.assertTrue(success, f"FreeFEMスクリプト実行エラー: {stderr}")
        
        # 結果を読み込み
        result_array = self.ff.read_int_array("output_int_array")
        
        # 期待される結果: 各要素に10を加算
        expected_array = test_array + 10
        
        # 結果を検証
        np.testing.assert_array_equal(result_array, expected_array,
                                     "FreeFEMでの処理結果が期待値と一致しません")
        
        print(f"テスト成功: FreeFEMでの整数配列処理が正常に完了しました")
    
    def test_large_int_array(self):
        """大規模整数配列のテスト"""
        # 大きめの整数配列を作成
        size = 1000
        test_array = np.arange(size, dtype=np.int32)
        
        # 共有メモリに書き込み
        self.ff.write_int_array(test_array, "large_int_array")
        
        # 共有メモリから読み込み
        result_array = self.ff.read_int_array("large_int_array")
        
        # 結果を検証
        np.testing.assert_array_equal(result_array, test_array,
                                     "大規模配列の読み書きに問題があります")
        
        print(f"テスト成功: {size}要素の整数配列を正常に処理しました")
    
    def test_mixed_array_types(self):
        """異なる型の配列の相互変換テスト"""
        # 浮動小数点値を含む配列
        float_array = np.array([1.5, 2.7, 3.2, 4.9, 5.1])
        
        # 整数配列として書き込み (キャストが行われる)
        self.ff.write_int_array(float_array, "mixed_type_array")
        
        # 結果を読み込み
        result_array = self.ff.read_int_array("mixed_type_array")
        
        # 期待される結果: 小数点以下が切り捨てられる
        expected_array = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        
        # 結果を検証
        np.testing.assert_array_equal(result_array, expected_array,
                                     "型変換が正しく行われていません")
        
        print(f"テスト成功: 浮動小数点配列 {float_array} が正しく整数配列 {result_array} に変換されました")

def run_tests():
    """テストを実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIntArrayCommunication)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 