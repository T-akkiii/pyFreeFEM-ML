#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_freefem_plugin.py
FreeFEMプラグインのテスト用Pythonスクリプト

このスクリプトは、FreeFEMプラグイン（mmap-semaphore.so）の動作をPython側からテストします。
テストでは、複数のFreeFEMスクリプトを実行し、各機能が正しく動作するかを確認します。
"""

import os
import sys
import time
import logging
import argparse
import subprocess
from pathlib import Path
import numpy as np

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Pythonライブラリをインポート
from pyfreefem_ml.freefem_interface import FreeFEMInterface
from pyfreefem_ml.freefem_runner import FreeFEMRunner
from pyfreefem_ml.utils import is_wsl, get_freefem_path, normalize_path_for_freefem

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_freefem_plugin.log')
    ]
)
logger = logging.getLogger(__name__)

# テスト設定
TEST_SCRIPTS_DIR = project_root / "plugins" / "scripts" / "tests"

def run_test_script(script_name, timeout=30):
    """FreeFEMのテストスクリプトを実行する"""
    script_path = TEST_SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        logger.error(f"テストスクリプト {script_path} が見つかりません")
        return False
    
    # FreeFEMのパスを取得
    freefem_cmd = get_freefem_path()
    
    # スクリプトのパスをFreeFEM用に正規化
    ff_script_path = normalize_path_for_freefem(str(script_path))
    
    logger.info(f"テストスクリプト実行: {script_name}")
    cmd = [freefem_cmd, ff_script_path]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # 結果の出力
        logger.info(f"終了コード: {result.returncode}")
        if result.stdout:
            logger.info(f"標準出力:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"標準エラー出力:\n{result.stderr}")
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error(f"タイムアウト: スクリプトの実行が {timeout} 秒以内に完了しませんでした")
        return False
    except Exception as e:
        logger.error(f"スクリプト実行中にエラーが発生しました: {e}")
        return False

def test_basic_functionality():
    """基本機能のテスト"""
    logger.info("=== 基本機能テスト開始 ===")
    success = run_test_script("basic-test.edp")
    logger.info(f"基本機能テスト結果: {'成功' if success else '失敗'}")
    return success

def test_array_operations():
    """配列操作のテスト"""
    logger.info("=== 配列操作テスト開始 ===")
    success_real = run_test_script("array-test.edp")
    logger.info(f"浮動小数点配列テスト結果: {'成功' if success_real else '失敗'}")
    
    success_int = run_test_script("int-array-test.edp")
    logger.info(f"整数配列テスト結果: {'成功' if success_int else '失敗'}")
    
    return success_real and success_int

def test_string_operations():
    """文字列操作のテスト"""
    logger.info("=== 文字列操作テスト開始 ===")
    success = run_test_script("string-test.edp")
    logger.info(f"文字列操作テスト結果: {'成功' if success else '失敗'}")
    return success

def test_error_handling():
    """エラーハンドリングのテスト"""
    logger.info("=== エラーハンドリングテスト開始 ===")
    success = run_test_script("error-handling-test.edp")
    logger.info(f"エラーハンドリングテスト結果: {'成功' if success else '失敗'}")
    return success

def test_wsl_compatibility():
    """WSL互換性のテスト"""
    logger.info("=== WSL互換性テスト開始 ===")
    success = run_test_script("wsl-path-test.edp")
    logger.info(f"WSL互換性テスト結果: {'成功' if success else '失敗'}")
    return success

def test_python_freefem_communication():
    """Python-FreeFEM間通信テスト"""
    logger.info("=== Python-FreeFEM間通信テスト開始 ===")
    
    # FreeFEMインターフェースを初期化
    ff = FreeFEMInterface(debug=True)
    
    try:
        # 値の書き込みテスト
        int_value = 42
        double_value = 3.14159
        string_value = "Hello from Python"
        
        ff.write_int(int_value, "test_int")
        ff.write_double(double_value, "test_double")
        ff.write_string(string_value, "test_string")
        
        # スクリプトを実行して値を読み取り、書き込みを行う
        script = """
        load "mmap-semaphore"
        
        // 共有メモリから値を読み取り
        int intVal;
        real doubleVal;
        string stringVal;
        
        ShmReadInt("test_int", 0, intVal);
        ShmReadDouble("test_double", 0, doubleVal);
        ShmReadString("test_string", 0, stringVal, 100);
        
        cout << "Read from Python - Int: " << intVal << ", Double: " << doubleVal << ", String: " << stringVal << endl;
        
        // 値を変更して書き込み
        int newInt = intVal * 2;
        real newDouble = doubleVal * 2;
        string newString = "Hello from FreeFEM";
        
        ShmWriteInt("result_int", 0, newInt);
        ShmWriteDouble("result_double", 0, newDouble);
        ShmWriteString("result_string", 0, newString);
        
        cout << "Written back - Int: " << newInt << ", Double: " << newDouble << ", String: " << newString << endl;
        """
        
        result = ff.run_inline_script(script)
        if not result[0]:
            logger.error(f"スクリプト実行エラー: {result[2]}")
            return False
        
        # FreeFEMが書き込んだ値を読み取り
        result_int = ff.read_int("result_int")
        result_double = ff.read_double("result_double")
        result_string = ff.read_string("result_string")
        
        # 結果を検証
        success = (
            result_int == int_value * 2 and
            abs(result_double - double_value * 2) < 1e-10 and
            result_string == "Hello from FreeFEM"
        )
        
        if success:
            logger.info("Python-FreeFEM間の基本データ型通信テスト成功")
        else:
            logger.error("Python-FreeFEM間の基本データ型通信テスト失敗")
            logger.error(f"期待値: {int_value*2}, {double_value*2}, 'Hello from FreeFEM'")
            logger.error(f"実際値: {result_int}, {result_double}, '{result_string}'")
        
        # 配列通信テスト
        logger.info("配列通信テスト開始")
        
        # 浮動小数点配列
        double_array = np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype=np.float64)
        ff.write_array(double_array, "test_double_array")
        
        # 整数配列
        int_array = np.array([10, 20, 30, 40, 50], dtype=np.int32)
        ff.write_int_array(int_array, "test_int_array")
        
        # 配列操作スクリプト
        array_script = """
        load "mmap-semaphore"
        
        // 配列の読み込み
        real[int] doubleArr(5);
        int[int] intArr(5);
        
        ShmReadArray("test_double_array", doubleArr, ArrayInfo(5, 0));
        ShmReadIntArray("test_int_array", intArr, ArrayInfo(5, 0));
        
        cout << "Read double array: ";
        for (int i = 0; i < 5; i++)
            cout << doubleArr[i] << " ";
        cout << endl;
        
        cout << "Read int array: ";
        for (int i = 0; i < 5; i++)
            cout << intArr[i] << " ";
        cout << endl;
        
        // 配列を操作して書き込み
        for (int i = 0; i < 5; i++) {
            doubleArr[i] = doubleArr[i] * 2;
            intArr[i] = intArr[i] + 5;
        }
        
        ShmWriteArray("result_double_array", doubleArr, ArrayInfo(5, 0));
        ShmWriteIntArray("result_int_array", intArr, ArrayInfo(5, 0));
        """
        
        result = ff.run_inline_script(array_script)
        if not result[0]:
            logger.error(f"配列操作スクリプト実行エラー: {result[2]}")
            return False
        
        # 結果の配列を読み取り
        result_double_array = ff.read_array("result_double_array")
        result_int_array = ff.read_int_array("result_int_array")
        
        # 配列結果を検証
        double_success = np.allclose(result_double_array, double_array * 2)
        int_success = np.array_equal(result_int_array, int_array + 5)
        
        if double_success and int_success:
            logger.info("配列通信テスト成功")
        else:
            logger.error("配列通信テスト失敗")
            if not double_success:
                logger.error(f"浮動小数点配列不一致 - 期待値: {double_array * 2}")
                logger.error(f"実際値: {result_double_array}")
            if not int_success:
                logger.error(f"整数配列不一致 - 期待値: {int_array + 5}")
                logger.error(f"実際値: {result_int_array}")
        
        return success and double_success and int_success
        
    except Exception as e:
        logger.error(f"Python-FreeFEM間通信テスト中にエラーが発生しました: {e}")
        return False
    finally:
        # リソースの解放
        ff.cleanup()

def run_all_tests():
    """すべてのテストを実行"""
    results = {}
    
    results["basic"] = test_basic_functionality()
    results["array"] = test_array_operations()
    results["string"] = test_string_operations()
    results["error"] = test_error_handling()
    results["wsl"] = test_wsl_compatibility()
    results["communication"] = test_python_freefem_communication()
    
    # 結果の表示
    logger.info("=== テスト結果サマリー ===")
    all_passed = True
    for test_name, result in results.items():
        status = "成功" if result else "失敗"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("すべてのテストが成功しました！")
    else:
        logger.warning("一部のテストが失敗しました")
    
    return all_passed

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="FreeFEMプラグインのテスト")
    parser.add_argument("--test", choices=["basic", "array", "string", "error", "wsl", "communication", "all"],
                        default="all", help="実行するテストを指定")
    args = parser.parse_args()
    
    # WSL環境情報の表示
    wsl_status = "WSL環境" if is_wsl() else "非WSL環境"
    logger.info(f"システム環境: {wsl_status}")
    logger.info(f"FreeFEMパス: {get_freefem_path()}")
    
    # テストの実行
    if args.test == "basic":
        test_basic_functionality()
    elif args.test == "array":
        test_array_operations()
    elif args.test == "string":
        test_string_operations()
    elif args.test == "error":
        test_error_handling()
    elif args.test == "wsl":
        test_wsl_compatibility()
    elif args.test == "communication":
        test_python_freefem_communication()
    else:  # all
        run_all_tests()

if __name__ == "__main__":
    main() 