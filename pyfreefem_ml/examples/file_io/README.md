# ファイル入出力によるFreeFEMとPythonの連携

このディレクトリには、ファイル入出力を使用してFreeFEMとPythonの間でデータを交換する例が含まれています。

## 概要

共有メモリを使用せずに、単純なファイル入出力によってPythonとFreeFEMの間でデータを交換するサンプルコードです。
このアプローチは以下の利点があります：

- 共有メモリプラグインが必要ない
- すべてのプラットフォームで動作する
- デバッグが容易

## ファイル構成

- `file_io_wrapper.py`: Pythonラッパースクリプト
- `poisson_file_io.edp`: FreeFEMサンプルスクリプト（ポアソン方程式を解く）

## 使用方法

### 基本的な使い方

```python
from pyfreefem_ml.file_io import FreeFEMFileIO

# ファイル入出力インターフェースの初期化
freefem = FreeFEMFileIO(debug=True)

# スクリプトを実行して結果を取得
success, result, stdout, stderr = freefem.run_script(
    'poisson_file_io.edp',
    output_file='output.txt'
)

if success:
    print(f"結果: {result}")
else:
    print(f"エラー: {stderr}")
```

### サンプルの実行

このディレクトリのサンプルを直接実行することもできます：

```bash
cd examples/file_io
python file_io_wrapper.py
```

## 注意点

- 大量のデータを交換する場合、ファイル入出力は共有メモリよりも遅くなる可能性があります
- バイナリ形式での入出力を使用することで、パフォーマンスを向上させることができます 