# PyFreeFEM-ML

Python-FreeFEM共有メモリインターフェース - 効率的なデータ交換のためのライブラリ

## 概要

PyFreeFEM-MLは、PythonとFreeFEMの間でデータを効率的に交換するためのライブラリです。共有メモリを使用して高速なデータ転送を実現し、反復計算や最適化問題など、頻繁なデータ交換が必要なシミュレーションに適しています。

主な特徴：
- 共有メモリを使用した高速データ交換
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
- Python 3.12以上
- FreeFEM 4.10以上
- WSL2環境（Windows上）

### Pipでのインストール

```bash
pip install pyfreefem_ml
```

これにより、自動的に:
1. Pythonパッケージがインストールされます
2. FreeFEMプラグインがビルドされます
3. ビルドされたプラグインがFreeFEMのプラグインディレクトリにインストールされます

### 手動インストール

```bash
git clone https://github.com/yourusername/pyfreefem-ml.git
cd pyfreefem-ml
pip install -e .
```

## 使用方法

### 基本的な使用例

```python
from pyfreefem_ml import PyFreeFEM

# PyFreeFEMインスタンスを初期化
ff = PyFreeFEM()

# セッションを開始
ff.start_session()

# 変数を共有メモリに書き込み
ff.write_variable("x", 10)
ff.write_variable("y", [1, 2, 3, 4, 5])

# FreeFEMスクリプトを実行
result = ff.run_script("""
    load "mmap-semaphore"
    
    // 共有メモリから値を読み取り
    int x = ShmReadInt("x");
    real[int] y(5);
    ShmReadArray("y", y);
    
    // 計算を実行
    real[int] z(5);
    for (int i = 0; i < 5; i++)
        z[i] = x * y[i];
    
    // 結果を共有メモリに書き込み
    ShmWriteArray("z", z);
""")

# 結果を読み取り
z = ff.read_variable("z")
print(z)  # [10, 20, 30, 40, 50]

# セッションを終了
ff.end_session()
```

### 応用例

より詳細な例は `examples` ディレクトリに含まれています:
- `basic_usage.py`: 基本的な使用方法
- `topo_opt_example.py`: トポロジー最適化の例

## ライセンス

MIT License 