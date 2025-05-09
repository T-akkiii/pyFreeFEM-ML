# PyFreeFEM-ML

Python-FreeFEM共有メモリインターフェース - 効率的なデータ交換のためのライブラリ

## 概要

PyFreeFEM-MLは、PythonとFreeFEMの間でデータを効率的に交換するためのライブラリです。OSに応じて自動的に最適な方法を選択します：
- Linux環境: 共有メモリを使用した高速データ転送
- Windows/macOS環境: ファイルI/Oを使用したデータ転送

主な特徴：
- マルチプラットフォーム対応（Linux、Windows、macOS）
- 統一インターフェース（`PyFreeFEM`クラス）でOSによる実装の違いを抽象化
- 整数、実数、配列データのサポート
- WSL2環境での動作
- 簡単に使えるPythonインターフェース
- エラーハンドリングとデバッグ機能

## ディレクトリ構造

```
pyfreefem_ml/
├── pyfreefem_ml/           # Pythonパッケージのソースコード
│   ├── __init__.py         # パッケージの初期化
│   ├── freefem_interface.py # FreeFEMインターフェース
│   ├── shm_manager.py      # 共有メモリマネージャー
│   ├── file_io.py          # ファイルI/Oインターフェース
│   ├── data_converter.py   # データ変換
│   ├── utils.py            # ユーティリティ関数
│   ├── freefem_runner.py   # FreeFEM実行
│   └── errors.py           # エラー定義
├── plugins/                # FreeFEMプラグイン
│   ├── src/                # プラグインのソースコード
│   │   └── mmap-semaphore.cpp # 共有メモリプラグイン実装
│   ├── scripts/            # FreeFEMスクリプト
│   │   ├── samples/        # サンプルスクリプト
│   │   └── tests/          # テストスクリプト
│   └── Makefile            # ビルド設定
├── examples/               # 使用例
│   ├── basic_usage.py      # 基本的な使用方法
│   ├── file_io/            # ファイルI/O使用例
│   ├── multi_array/        # 多次元配列の例
│   └── topo_opt_example.py # トポロジー最適化の例
├── tests/                  # テスト
│   ├── test_pyfreefem.py   # Pythonテスト
│   └── test_simple_shm.py  # 共有メモリテスト
├── docs/                   # ドキュメント
│   └── requirements.md     # 要件定義
├── setup.py                # インストール設定
└── README.md               # 本ドキュメント
```

## インストール方法

### 前提条件
- Python 3.11以上
- FreeFEM 4.10以上
- (Linuxのみ) 共有メモリ機能に必要なシステムライブラリ

### Pipでのインストール

```bash
pip install pyfreefem_ml
```

これにより、自動的に:
1. Pythonパッケージがインストールされます
2. Linux環境の場合のみ、FreeFEMプラグインがビルドされインストールされます

### 手動インストール

```bash
git clone https://github.com/yourusername/pyfreefem-ml.git
cd pyfreefem-ml
pip install -e .
```

## 使用方法

### 統一インターフェースの使用例

```python
from pyfreefem_ml import PyFreeFEM
import numpy as np

# PyFreeFEMインスタンスを初期化（OSに応じて適切な実装を自動選択）
ff = PyFreeFEM(debug=True)

# セッションを開始
ff.start_session()

try:
    # データの準備
    input_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    
    # FreeFEMスクリプトを実行
    if ff.implementation == 'shm':  # Linux環境の場合
        # 変数を共有メモリに書き込み
        ff.write_array("input_data", input_data)
        
        # スクリプトを実行
        result = ff.run_script("script.edp")
        
        # 結果を読み取り
        output_data = ff.read_array("output_data")
    else:  # Windows/macOS環境の場合
        # ファイルI/Oを使用してスクリプト実行
        success, output_data, stdout, stderr = ff.run_script(
            "script.edp", 
            input_data=input_data
        )
    
    print("結果:", output_data)

finally:
    # セッションを終了
    ff.end_session()
```

### プラットフォームに依存しない使用例

統一インターフェースを使用すると、OSの違いを意識せずに同じコードで実行できます：

```python
from pyfreefem_ml import PyFreeFEM
import numpy as np

# PyFreeFEMインスタンスを初期化
ff = PyFreeFEM(debug=True)

# セッション開始
ff.start_session()

try:
    # 入力データの準備
    input_array = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    
    # FreeFEMスクリプトの内容を定義
    script_content = """
    // 入力データ受け取り用の変数
    real[int] input(5);
    
    // システムによって適切な方法でデータを読み込み
    #if _WIN32 || __APPLE__
        // ファイルから読み込み
        ifstream f("input.txt");
        for(int i = 0; i < 5; i++) f >> input[i];
    #else
        // 共有メモリから読み込み
        load "mmap-semaphore"
        ShmReadArray("input_data", input);
    #endif
    
    // データ処理
    real[int] output(5);
    for(int i = 0; i < 5; i++) output[i] = input[i] * 2;
    
    // 結果を出力
    #if _WIN32 || __APPLE__
        // ファイルに書き込み
        ofstream g("output.txt");
        for(int i = 0; i < 5; i++) g << output[i] << " ";
    #else
        // 共有メモリに書き込み
        ShmWriteArray("output_data", output);
    #endif
    """
    
    # データをセット（共有メモリの場合）
    if ff.implementation == 'shm':
        ff.write_array("input_data", input_array)
    
    # スクリプト実行
    result = ff.run_inline_script(script_content, input_data=input_array)
    
    # 結果取得
    if ff.implementation == 'shm':
        output_array = ff.read_array("output_data")
        print("結果:", output_array)
    else:
        success, output_array, stdout, stderr = result
        if success:
            print("結果:", output_array)
        else:
            print("エラー:", stderr)

finally:
    # セッションを終了
    ff.end_session()
```

## ファイル入出力インターフェース

共有メモリプラグインが利用できない環境（Windows、macOS）では、自動的にファイル入出力を使用したデータ交換が利用されます：

```python
from pyfreefem_ml import PyFreeFEM

# 統一インターフェースを使用（Windowsでは自動的にファイルI/Oを使用）
freefem = PyFreeFEM(debug=True)

# スクリプトを実行して結果を取得
success, result, stdout, stderr = freefem.run_script(
    'path/to/script.edp',
    input_data=np.array([1.0, 2.0, 3.0]),  # 入力データ
    output_file='output.txt',               # 出力ファイル名
    metadata_file='metadata.txt'            # メタデータファイル名（オプション）
)

if success:
    print(f"結果: {result}")
else:
    print(f"エラー: {stderr}")
```

### 多次元配列の処理

多次元配列を扱う場合は、メタデータファイルを使用して配列の形状情報を保存します：

```python
# FreeFEMスクリプト内でのメタデータ出力例
meta << nfunctions << " " << npoints << endl;
meta << nx+1 << " " << ny+1 << endl;
```

詳細な使用例は `examples/file_io` および `examples/multi_array` ディレクトリを参照してください。

## プラットフォーム固有の考慮事項

### Linux
- 共有メモリを使用した高速データ転送が利用可能
- `sysv_ipc` パッケージが必要（自動インストール）
- 共有メモリプラグインのインストールが必要

### Windows
- ファイルI/O方式を使用したデータ転送
- WSL環境でFreeFEMを実行する場合は `wsl_mode=True` を指定
- パスの扱いに注意が必要（WSLとWindows間のパス変換）

### macOS
- ファイルI/O方式を使用したデータ転送
- 標準的なmacOS環境でFreeFEMを実行
