# 多次元配列のFreeFEMとPython間交換

このディレクトリには、多次元配列データをFreeFEMとPython間で交換するためのサンプルコードが含まれています。

## 概要

FreeFEMでは2次元メッシュ上の複数の関数（スカラー場、ベクトル場など）を計算することができます。
これらの多次元データをPythonに効率的に転送し、処理する方法を示すサンプルです。

## アプローチ

多次元配列を交換するために、以下のアプローチを採用しています：

1. **メタデータファイル**: 配列の形状情報を別ファイルに保存
2. **連続データ格納**: 複数の配列を1つのファイルに連続して格納
3. **適切な再構築**: メタデータに基づいてPython側でデータを適切な形状に再構築

## ファイル構成

- `multi_array_io.edp`: FreeFEMスクリプト（複数のテスト関数を計算）
- `multi_array_io.py`: Pythonスクリプト（データの読み込みと可視化）

## 使用方法

### サンプルの実行

```bash
cd examples/multi_array
python multi_array_io.py
```

このスクリプトは以下を実行します：
1. FreeFEMスクリプトを実行して多次元データを生成
2. 生成されたデータとメタデータを読み込み
3. データを適切な多次元配列形式に変換
4. 2Dと3Dの可視化を生成

### FreeFEMスクリプトで多次元データを生成

```cpp
// メタデータの書き込み
meta << nfunctions << " " << npoints << endl;
meta << nx+1 << " " << ny+1 << endl;

// 複数の関数のデータを連続して書き込む
for (int f = 0; f < nfunctions; f++) {
    Vh currentU;
    if (f == 0) currentU = u1;
    else if (f == 1) currentU = u2;
    else currentU = u3;
    
    for (int i = 0; i < currentU[].n; i++) {
        out << currentU[][i] << endl;
    }
}
```

### Pythonでの多次元データの読み込み

```python
from pyfreefem_ml.file_io import FreeFEMFileIO

# ファイル入出力インターフェースの初期化
freefem = FreeFEMFileIO(debug=True)

# スクリプトを実行して結果を取得
success, result, stdout, stderr = freefem.run_script(
    'multi_array_io.edp',
    output_file='multi_array_output.txt',
    metadata_file='multi_array_metadata.txt'
)

# result は自動的に適切な多次元配列に変換される
# 3次元配列の場合: [関数の数, y方向の点数, x方向の点数]
```

## 応用例

このアプローチは以下のような応用が可能です：

1. 複数の物理量のシミュレーション結果の可視化
2. 時間発展問題における複数の時間ステップの結果保存
3. パラメトリック解析での複数のパラメータに対する結果の比較 