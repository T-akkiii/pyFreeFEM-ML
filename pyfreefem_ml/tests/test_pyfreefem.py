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
import logging
from pathlib import Path

# カレントディレクトリをスクリプトの位置に設定
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

# プロジェクトルートを取得してパスに追加
project_root = script_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# PyFreeFEMライブラリをインポート
from src.pyfreefem.freefem_interface import FreeFEMInterface
from src.pyfreefem.errors import SharedMemoryError, FreeFEMExecutionError, DataTypeError

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_pyfreefem_python.log')
    ]
)
logger = logging.getLogger(__name__)

def test_pyfreefem():
    """PyFreeFEMライブラリの基本機能をテストする関数"""
    logger.info("PyFreeFEMテスト開始")
    
    try:
        # FreeFEMインターフェースの作成
        # 共有メモリのサイズを1MBに設定
        pyff = FreeFEMInterface(shm_name="pyfreefem_shm", shm_size=1024*1024)
        logger.info("FreeFEMインターフェースインスタンスを作成しました")
        
        # 基本データ型の書き込みテスト
        # ------------------
        logger.info("データ書き込みテスト開始")
        
        # 整数値のテスト
        test_int = 42
        pyff.set_data("test_int", test_int)
        logger.info(f"整数値を書き込みました: test_int = {test_int}")
        
        # 浮動小数点値のテスト
        test_double = 3.14159
        pyff.set_data("test_double", test_double)
        logger.info(f"浮動小数点値を書き込みました: test_double = {test_double}")
        
        # 文字列のテスト
        test_string = "こんにちは、PyFreeFEM!"
        pyff.set_data("test_string", test_string)
        logger.info(f"文字列を書き込みました: test_string = {test_string}")
        
        # 配列のテスト
        test_array = np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype=np.float64)
        pyff.set_data("test_array", test_array)
        logger.info(f"配列を書き込みました: test_array = {test_array}")
        
        # FreeFEMスクリプトの実行
        # ------------------
        logger.info("FreeFEMスクリプト実行テスト開始")
        
        # テスト用FreeFEMスクリプトのパス
        freefem_script = os.path.join(project_root, "src", "pyfreefem", "freefem", "test_pyfreefem.edp")
        
        # スクリプトを実行
        result = pyff.run_script(freefem_script)
        logger.info(f"FreeFEMスクリプトの実行結果: {'成功' if result.success else '失敗'}")
        
        if result.output:
            logger.info(f"出力:\n{result.output}")
        
        # FreeFEMから処理結果を読み込む
        # ------------------
        logger.info("処理結果読み込みテスト開始")
        
        # テストが完了したかチェック
        max_wait = 30  # 最大待機時間（秒）
        start_time = time.time()
        test_completed = 0
        
        while test_completed == 0 and (time.time() - start_time) < max_wait:
            try:
                test_completed = pyff.get_data("test_completed")
                if test_completed == 0:
                    logger.info("FreeFEMの処理が完了するのを待っています...")
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"テスト完了フラグの読み込み中にエラーが発生しました: {e}")
                time.sleep(1)
        
        if test_completed != 1:
            logger.error(f"FreeFEMの処理がタイムアウトまたはエラーが発生しました")
            return False
        
        # 処理結果を読み込む
        result_int = pyff.get_data("result_int")
        logger.info(f"整数値の処理結果: result_int = {result_int}")
        
        result_double = pyff.get_data("result_double")
        logger.info(f"浮動小数点値の処理結果: result_double = {result_double}")
        
        result_string = pyff.get_data("result_string")
        logger.info(f"文字列の処理結果: result_string = {result_string}")
        
        # 配列の処理結果を読み込む
        result_array = pyff.get_data("result_array")
        logger.info(f"配列の処理結果: result_array = {result_array}")
        
        # 結果の検証
        # ------------------
        logger.info("処理結果の検証開始")
        
        # 期待される値との比較
        expected_int = test_int + 10
        expected_double = test_double * 2.0
        expected_string = test_string + " [処理済]"
        expected_array = test_array + 5.0
        
        success = True
        
        if result_int != expected_int:
            logger.error(f"整数値の検証エラー: 期待={expected_int}, 実際={result_int}")
            success = False
        
        if abs(result_double - expected_double) > 1e-10:
            logger.error(f"浮動小数点値の検証エラー: 期待={expected_double}, 実際={result_double}")
            success = False
        
        if result_string != expected_string:
            logger.error(f"文字列の検証エラー: 期待={expected_string}, 実際={result_string}")
            success = False
        
        if not np.allclose(result_array, expected_array):
            logger.error(f"配列の検証エラー: 期待={expected_array}, 実際={result_array}")
            success = False
        
        if success:
            logger.info("テスト結果: 成功 - すべての検証が正常に完了しました")
        else:
            logger.error("テスト結果: 失敗 - 一部の検証に失敗しました")
        
        # 結果のサマリーをファイルに書き込む
        with open("test_pyfreefem_result.txt", "w", encoding="utf-8") as f:
            f.write("PyFreeFEMテスト結果サマリー\n")
            f.write("======================\n\n")
            f.write(f"テスト結果: {'成功' if success else '失敗'}\n\n")
            
            f.write("入力値:\n")
            f.write(f"  整数値: {test_int}\n")
            f.write(f"  浮動小数点値: {test_double}\n")
            f.write(f"  文字列: {test_string}\n")
            f.write(f"  配列: {test_array}\n\n")
            
            f.write("処理結果:\n")
            f.write(f"  整数値: {result_int}\n")
            f.write(f"  浮動小数点値: {result_double}\n")
            f.write(f"  文字列: {result_string}\n")
            f.write(f"  配列: {result_array}\n")
        
        # クリーンアップ
        pyff.cleanup()
        logger.info("リソースをクリーンアップしました")
        
        return success
    
    except SharedMemoryError as e:
        logger.error(f"共有メモリエラー: {e}")
        return False
    except FreeFEMExecutionError as e:
        logger.error(f"FreeFEM実行エラー: {e}")
        return False
    except DataTypeError as e:
        logger.error(f"データ型エラー: {e}")
        return False
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        logger.info("PyFreeFEMテスト終了")

if __name__ == "__main__":
    success = test_pyfreefem()
    sys.exit(0 if success else 1) 