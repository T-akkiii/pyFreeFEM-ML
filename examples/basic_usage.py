#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyFreeFEMの基本的な使用例

このスクリプトはPyFreeFEMの基本的な使い方を示します。
"""

import os
import sys
import numpy as np
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from pyfreefem import PyFreeFEM

def main():
    """PyFreeFEMの基本的な使用例"""
    print("PyFreeFEMの基本的な使用例を開始します")
    
    # PyFreeFEMインスタンスを作成
    pff = PyFreeFEM(freefem_path="FreeFem++")
    
    # セッションを開始
    session_id = pff.start_session()
    print(f"セッションを開始しました: {session_id}")
    
    try:
        # 変数をPythonから共有メモリに書き込む
        pff.write_variable("scalar_int", 42)
        pff.write_variable("scalar_float", 3.14159)
        pff.write_variable("text_message", "Hello from Python!")
        
        # NumPy配列を書き込む
        matrix = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64)
        pff.write_variable("matrix", matrix)
        
        # FreeFEMスクリプトの内容
        script = """
        // Python側から送られた変数を読み込む
        int int_value;
        GetFromMmap(shm, "scalar_int", int_value);
        log("整数値を読み込みました: " + int_value);
        
        real float_value;
        GetFromMmap(shm, "scalar_float", float_value);
        log("浮動小数点数を読み込みました: " + float_value);
        
        string text;
        GetFromMmap(shm, "text_message", text);
        log("文字列を読み込みました: " + text);
        
        // 行列の次元を取得
        int rows = 2;
        int cols = 3;
        
        // 行列要素を読み込む
        real[int,int] mat(rows, cols);
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                real val;
                GetFromMmap(shm, "matrix_" + i + "_" + j, val);
                mat(i,j) = val;
                log("matrix(" + i + "," + j + ") = " + val);
            }
        }
        
        // 計算結果を共有メモリに書き込む
        real sum = 0;
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                sum += mat(i,j);
            }
        }
        
        SetInMmap(shm, "matrix_sum", sum);
        log("行列の合計を計算しました: " + sum);
        
        // スカラー結果を共有メモリに書き込む
        real pi_squared = float_value * float_value;
        SetInMmap(shm, "pi_squared", pi_squared);
        log("π²を計算しました: " + pi_squared);
        
        // 文字列を加工して返す
        string response = "FreeFEMから応答: " + text + " (処理済み)";
        SetInMmap(shm, "response_text", response);
        log("応答メッセージを設定しました");
        """
        
        # FreeFEMスクリプトを実行
        print("FreeFEMスクリプトを実行します...")
        return_code, stdout, stderr = pff.run_script(script)
        
        if return_code != 0:
            print(f"FreeFEMスクリプトの実行に失敗しました (コード: {return_code})")
            if stderr:
                print(f"エラー出力: {stderr}")
            return 1
        
        print("FreeFEMスクリプトの実行に成功しました")
        
        # FreeFEMからの結果を読み込む
        matrix_sum = pff.read_variable("matrix_sum")
        pi_squared = pff.read_variable("pi_squared")
        response_text = pff.read_variable("response_text")
        
        print("\n結果:")
        print(f"行列の合計: {matrix_sum}")
        print(f"π²: {pi_squared}")
        print(f"応答テキスト: {response_text}")
        
        # 検証
        expected_sum = np.sum(matrix)
        expected_pi_squared = 3.14159 * 3.14159
        
        print("\n検証:")
        print(f"行列合計の検証: {expected_sum} (期待値) vs {matrix_sum} (実際値)")
        print(f"π²の検証: {expected_pi_squared} (期待値) vs {pi_squared} (実際値)")
        
        if abs(expected_sum - matrix_sum) < 1e-10 and abs(expected_pi_squared - pi_squared) < 1e-10:
            print("検証成功! 計算結果は期待値と一致しています")
        else:
            print("検証失敗: 計算結果が期待値と一致しません")
        
        # 共有メモリ内の全変数を一覧表示
        print("\n共有メモリの変数一覧:")
        for var in pff.list_variables():
            print(f"  - {var['name']} (型: {var['type']})")
        
        return 0
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return 1
    
    finally:
        # セッションを終了
        pff.end_session()
        print("セッションを終了しました")

if __name__ == "__main__":
    sys.exit(main()) 