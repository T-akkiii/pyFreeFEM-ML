#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基本的な共有メモリ通信のテストスクリプト
"""

import os
import sys
import numpy as np
from pathlib import Path

# プロジェクトルートへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# FreeFEMインターフェースをインポート
from pyfreefem_ml.freefem_interface import FreeFEMInterface
from pyfreefem_ml.plugin_installer import install_plugin

def main():
    """共有メモリ通信のテスト実行"""
    print("===== 共有メモリ通信テスト =====")
    
    # プラグインのインストール状態を確認
    print("プラグインのインストール状態を確認しています...")
    install_plugin(debug=True)
    
    # 環境変数を設定
    os.environ['FF_SHM_NAME'] = 'test_shm'
    os.environ['FF_SHM_SIZE'] = str(1024 * 1024)  # 1MB
    
    # FreeFEMインターフェースの初期化（プラグインの自動インストールを有効に）
    print("FreeFEMインターフェースを初期化しています...")
    freefem = FreeFEMInterface(
        wsl_mode=False,  # WSL内から実行するのでFalseに設定
        debug=True,
        auto_install_plugin=True  # プラグインの自動インストールを有効化
    )

    try:
        # テスト用の配列を準備
        test_array = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        print(f"Python: 共有メモリに書き込む配列: {test_array}")
        
        # 配列を共有メモリに書き込み
        freefem.write_array("test_array", test_array)

        # テストスクリプトのパス
        script_path = Path(__file__).parent / "resources" / "shared_memory_test.edp"
        if not script_path.exists():
            # スクリプトが見つからない場合、テスト用のスクリプトを生成
            print(f"テストスクリプトが見つかりません: {script_path}")
            print("インラインスクリプトを代わりに使用します")
            
            # FFスクリプトの設定
            script = """
            // 共有メモリプラグインのロード
            load "mmap-semaphore"
            
            cout << "FreeFEM: 共有メモリテストを開始します" << endl;
            
            // 共有メモリからデータを読み込む
            real[int] arr(5);
            try {
                cout << "FreeFEM: 配列を共有メモリから読み込みます..." << endl;
                ShmReadDoubleArray("test_array", arr);
                
                cout << "FreeFEM: 読み込んだ配列: ";
                for (int i = 0; i < 5; i++) {
                    cout << arr[i] << " ";
                }
                cout << endl;
                
                // データを処理（2倍する）
                for (int i = 0; i < 5; i++) {
                    arr[i] = arr[i] * 2;
                }
                
                cout << "FreeFEM: 処理後の配列（2倍）: ";
                for (int i = 0; i < 5; i++) {
                    cout << arr[i] << " ";
                }
                cout << endl;
                
                // 処理した結果を共有メモリに書き戻す
                cout << "FreeFEM: 結果を共有メモリに書き込みます..." << endl;
                ShmWriteDoubleArray("result_array", arr);
                cout << "FreeFEM: データを共有メモリに書き込みました" << endl;
            } catch(...) {
                cout << "FreeFEM: 共有メモリ操作中にエラーが発生しました" << endl;
                exit(1);
            }
            
            cout << "FreeFEM: 共有メモリテストが完了しました" << endl;
            """

            # スクリプトの実行
            print("Python: インラインFreeFEMスクリプトを実行します...")
            success, output, error = freefem.run_inline_script(script)
        else:
            # スクリプトが存在する場合はそれを実行
            print(f"Python: テストスクリプトを実行します: {script_path}")
            success, output, error = freefem.run_script(str(script_path))
        
        # 実行結果の表示
        if not success:
            print(f"Python: FreeFEMスクリプトの実行に失敗しました")
            print(f"エラー: {error}")
            if output:
                print(f"出力: {output}")
        else:
            print("Python: FreeFEMスクリプトの実行に成功しました")
            print(f"出力: {output}")
            
            # 共有メモリから結果を読み込む
            try:
                result_array = freefem.read_array("result_array")
                print(f"Python: 共有メモリから読み込んだ結果: {result_array}")
                
                # 結果の検証
                expected = test_array * 2
                if np.allclose(result_array, expected):
                    print("Python: テスト成功！ 結果は期待通りです")
                else:
                    print(f"Python: テスト失敗！ 期待値: {expected}, 実際の値: {result_array}")
            except Exception as e:
                print(f"Python: 結果の読み込み中にエラー: {e}")
        
    except Exception as e:
        print(f"Python: テスト実行中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # リソースのクリーンアップ
        print("Python: リソースをクリーンアップします...")
        freefem.cleanup()
        print("Python: クリーンアップ完了")
        print("===== テスト終了 =====")

if __name__ == "__main__":
    main() 