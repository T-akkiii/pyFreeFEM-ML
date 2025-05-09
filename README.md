# PyFreeFEM-ML

Python-FreeFEM共有メモリインターフェース - 効率的なデータ交換のためのライブラリ

## 概要

PyFreeFEM-MLは、PythonとFreeFEMの間でデータを効率的に交換するためのライブラリです。共有メモリを使用して高速なデータ転送を実現しますが、ファイル入出力を使用した代替手段も提供しています。反復計算や最適化問題など、頻繁なデータ交換が必要なシミュレーションに適しています。

主な特徴：
- 共有メモリを使用した高速データ交換
- ファイル入出力を使用した代替手段（プラグインが使用できない環境向け）
- 整数、実数、配列データのサポート
- 多次元配列のサポート（ファイル入出力方式）
- WSL2環境での動作
- 簡単に使えるPythonインターフェース
- エラーハンドリングとデバッグ機能

## プロジェクト構造

```
pyfreefem_ml/          # メインパッケージディレクトリ
├── __init__.py        # パッケージ初期化
├── freefem_interface.py # 主要なインターフェースクラス
├── shm_manager.py     # 共有メモリ管理
├── file_io.py         # ファイル入出力インターフェース
├── plugins/           # FreeFEMプラグイン
├── examples/          # 使用例
│   ├── basic_usage.py # 基本的な使用例
│   ├── file_io/       # ファイル入出力の例
│   └── multi_array/   # 多次元配列処理の例
├── tests/             # テスト
└── docs/              # ドキュメント
```

## インストール方法

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/pyfreefem-ml.git
cd pyfreefem-ml

# パッケージとFreeFEMプラグインのインストール
pip install -e pyfreefem_ml
```

## 使用方法

### 共有メモリを使用する方法

```python
from pyfreefem_ml.freefem_interface import FreeFEMInterface
import numpy as np

# FreeFEMインターフェースの初期化
freefem = FreeFEMInterface(debug=True)

# テスト用の配列を準備
test_array = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

# 配列を共有メモリに書き込み
freefem.write_array("test_data", test_array)

# FreeFEMスクリプトを実行
script = """
// 共有メモリからデータを読み込む
real[int] data(5);
ShmReadDoubleArray("test_data", data);

// データを処理
for (int i = 0; i < 5; i++) {
    data[i] = data[i] + 1;
}

// 処理したデータを共有メモリに書き戻す
ShmWriteDoubleArray("test_data", data);
"""

success, output, error = freefem.run_inline_script(script)

# 処理結果を取得
if success:
    result = freefem.read_array("test_data")
    print(f"処理結果: {result}")  # [2.0, 3.0, 4.0, 5.0, 6.0]
```

### ファイル入出力を使用する方法

共有メモリプラグインが利用できない環境では、ファイル入出力方式を使用できます：

```python
from pyfreefem_ml.file_io import FreeFEMFileIO
import numpy as np

# ファイル入出力インターフェースの初期化
freefem = FreeFEMFileIO(debug=True)

# FreeFEMスクリプトを実行して結果を取得
success, result, stdout, stderr = freefem.run_script(
    'path/to/script.edp',
    input_data=np.array([1.0, 2.0, 3.0]),  # 入力データ（オプション）
    output_file='output.txt'                # 出力ファイル名
)

if success:
    print(f"結果: {result}")
```

## 多次元配列の処理

多次元配列を扱う場合は、メタデータファイルを使用して配列の形状情報を保存します：

```python
# FreeFEMスクリプト内でのメタデータ出力例
meta << nfunctions << " " << npoints << endl;
meta << nx+1 << " " << ny+1 << endl;

# Pythonでの処理
success, result, stdout, stderr = freefem.run_script(
    'multi_array_script.edp',
    output_file='output.txt',
    metadata_file='metadata.txt'  # メタデータファイル
)
```

詳細な使用例は `examples/file_io` および `examples/multi_array` ディレクトリを参照してください。

## ライセンス

MIT License 

## 問題の診断と解決策

### WSL環境での実行の問題

WSL環境でpyFreeFEM-MLを実行する際、共有メモリ関連で以下の問題が発生することがあります：

1. FreeFEMに`mmap-semaphore`プラグインが見つからない
2. 共有メモリセグメントのアクセス権限の問題
3. WSL内からさらにWSLコマンドを実行できない問題

### 解決策

1. プラグインのインストール：
   ```bash
   sudo cp plugins/lib/mmap-semaphore.so /usr/local/lib/ff++/4.10/
   ```

2. 環境変数の設定：
   ```bash
   export FF_LOADPATH=/usr/local/lib/ff++/4.10
   export FF_INCLUDEPATH=/usr/local/lib/ff++/4.10/idp
   ```

3. 共有メモリが使用できない場合の代替手段:
   - ファイル入出力ベースの方法を使用する
   - `pyfreefem_ml.file_io.FreeFEMFileIO` クラスを使用 