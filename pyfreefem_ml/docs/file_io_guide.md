# PyFreeFEM-ML ファイルIO通信ガイド

このガイドでは、PyFreeFEM-MLライブラリを使用して、ファイル入出力（IO）を介してPythonとFreeFEM間でデータをやり取りする方法を説明します。

## 目次

1. [概要](#概要)
2. [セットアップ](#セットアップ)
3. [基本的な使用方法](#基本的な使用方法)
4. [データ形式](#データ形式)
5. [高度な使用方法](#高度な使用方法)
6. [共有メモリとの比較](#共有メモリとの比較)
7. [サンプルコード](#サンプルコード)
8. [トラブルシューティング](#トラブルシューティング)
9. [最新の改善点（2024年3月）](#最新の改善点（2024年3月）)

## 概要

ファイルIOを使用したデータ通信は、共有メモリの代替手段として提供されています。このアプローチには以下の利点があります：

- 共有メモリプラグインのインストールが不要
- プラットフォーム依存性が低い（すべてのOS環境で動作）
- デバッグが容易
- 中間結果を永続化できる

一方で以下の制限もあります：

- 大量のデータ交換では共有メモリよりも低速
- ディスクI/O操作による追加のオーバーヘッド

## セットアップ

### 必要条件

- Python 3.6以上
- FreeFEM 4.0以上
- NumPy
- PyFreeFEM-MLライブラリ

### インストール

PyFreeFEM-MLがすでにインストールされていれば、追加のインストール手順は不要です。ファイルIO機能は標準で含まれています。

```bash
# インストールされていない場合は以下を実行
pip install pyfreefem-ml
```

## 基本的な使用方法

### Pythonコード

```python
from pyfreefem_ml.file_io import FreeFEMFileIO

# ファイルIOインターフェースの初期化
ff = FreeFEMFileIO(
    freefem_path='FreeFem++',  # FreeFEM実行ファイルのパス
    working_dir=None,          # 作業ディレクトリ（Noneの場合は現在のディレクトリ）
    debug=True                 # デバッグモード（詳細な出力）
)

# 入力データの準備（例：NumPy配列）
import numpy as np
input_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

# FreeFEMスクリプトを実行（データを渡して結果を取得）
success, result, stdout, stderr = ff.run_script(
    script_path='path/to/script.edp',  # FreeFEMスクリプトのパス
    input_data=input_data,             # 入力データ（省略可能）
    input_file='input.txt',            # 入力ファイル名
    output_file='output.txt',          # 出力ファイル名
    metadata_file=None                 # メタデータファイル名（多次元配列用、省略可能）
)

# 結果の確認
if success:
    print("スクリプト実行成功")
    print(f"結果: {result}")
else:
    print(f"スクリプト実行失敗: {stderr}")
```

### FreeFEMスクリプト

```c++
// example.edp

// ファイルパスは外部から設定される、もしくはデフォルト値を使用
string inputFile = "input.txt";   // 入力ファイル名（Pythonと一致させる）
string outputFile = "output.txt"; // 出力ファイル名（Pythonと一致させる）

// 実行開始メッセージ
cout << "======= FreeFEMスクリプト実行開始 =======" << endl;

// 入力ファイルからデータを読み込む
real[int] inputData(0); // サイズ0の配列で初期化
{
    // ファイルオープン
    ifstream f(inputFile);
    
    // データ数を数える
    string line;
    int count = 0;
    while (!f.eof()) {
        getline(f, line);
        if (line.length() > 0) count++;
    }
    
    // 配列リサイズとデータ読み込み
    f.close();
    f = ifstream(inputFile);
    inputData.resize(count);
    for (int i = 0; i < count; i++) {
        f >> inputData[i];
    }
    
    cout << "入力ファイルから " << count << " 個のデータを読み込みました" << endl;
}

// データ処理（例：各値を2倍）
real[int] outputData(inputData.n);
for (int i = 0; i < inputData.n; i++) {
    outputData[i] = 2 * inputData[i];
}

// 出力ファイルにデータを書き込む
{
    ofstream f(outputFile);
    f.precision(16); // 倍精度で出力
    
    for (int i = 0; i < outputData.n; i++) {
        f << outputData[i] << endl;
    }
    
    cout << outputData.n << " 個のデータを出力ファイルに書き込みました" << endl;
}

// 実行終了メッセージ
cout << "======= FreeFEMスクリプト実行完了 =======" << endl;
```

## データ形式

### デフォルトのデータ形式

デフォルトでは、データはテキスト形式のCSVファイルとして交換されます：

- **入力ファイル（Python → FreeFEM）**: 1列のテキストファイルで、各行に1つの値
- **出力ファイル（FreeFEM → Python）**: 1列のテキストファイルで、各行に1つの値

### サポートされているデータ型

- 数値（整数、浮動小数点数）
- 1次元配列（ベクトル）
- 2次元配列（行列）
- 多次元配列（メタデータファイルを使用）

## 高度な使用方法

### 多次元配列（行列）のサポート

多次元配列を交換するには、追加のメタデータファイルを使用します：

#### Python側

```python
# 2次元配列の例
matrix_data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

# メタデータファイルを指定して実行
success, result, stdout, stderr = ff.run_script(
    script_path='matrix_example.edp',
    input_data=matrix_data.flatten(),  # 1次元に平坦化
    input_file='matrix_input.txt',
    output_file='matrix_output.txt',
    metadata_file='matrix_metadata.txt'  # 形状情報のメタデータ
)

# メタデータを手動で作成（run_scriptの前に実行）
with open('matrix_metadata.txt', 'w') as f:
    f.write(f"1 {matrix_data.size}\n")  # 1つの配列とその要素数
    f.write(f"{matrix_data.shape[1]} {matrix_data.shape[0]}\n")  # 列数 行数
```

#### FreeFEM側

```c++
// メタデータファイルからマトリックスの形状を読み取る
int nx, ny;
{
    ifstream f("matrix_metadata.txt");
    int n_arrays, n_elements;
    f >> n_arrays >> n_elements;
    f >> nx >> ny;
}

// 入力データを読み込み、2次元配列に変換
real[int, int] matrix(ny, nx);
{
    int idx = 0;
    real[int] flat_data(nx * ny);
    ifstream f("matrix_input.txt");
    
    for (int i = 0; i < nx * ny; i++) {
        f >> flat_data[i];
    }
    
    for (int i = 0; i < ny; i++) {
        for (int j = 0; j < nx; j++) {
            matrix(i, j) = flat_data[idx++];
        }
    }
}

// 処理後、出力と同じようなメタデータを書き込む
{
    ofstream f("matrix_metadata.txt");
    f << "1 " << nx * ny << endl;
    f << nx << " " << ny << endl;
}
```

### WSL環境での使用

WSL（Windows Subsystem for Linux）環境でFreeFEMを実行する場合、パスの設定に注意が必要です：

```python
# WSL環境での設定例
ff = FreeFEMFileIO(
    freefem_path='wsl FreeFem++',  # WSL経由でFreeFEMを実行
    working_dir='/mnt/c/path/to/working/dir'  # WSLパス形式
)

# または、utils.pyのWSLパス変換関数を使用
from pyfreefem_ml.utils import convert_windows_to_wsl_path
wsl_path = convert_windows_to_wsl_path('C:\\path\\to\\directory')
```

## 共有メモリとの比較

### ファイルIO vs 共有メモリ

| 側面 | ファイルIO | 共有メモリ |
|------|-----------|-----------|
| 速度 | 低速（特に大きなデータ） | 高速 |
| セットアップ | 簡単（追加インストール不要） | 複雑（プラグインのインストールが必要） |
| プラットフォーム互換性 | 高い（すべてのOS） | 限定的（特にWSL環境で問題が発生する場合あり） |
| デバッグ | 容易（中間ファイルを検査可能） | 困難（メモリ内容の直接検査が難しい） |
| メモリ使用量 | 低い（ディスクストレージを使用） | 高い（全データがメモリに保持される） |
| 大規模データ | 制限あり（ディスクI/Oがボトルネック） | 効率的（サイズ制限はあるが高速） |

### 使い分けの指針

- **ファイルIOが適している場合**:
  - 小〜中規模のデータ交換（数MB以下）
  - プラグインのインストールが困難な環境
  - クロスプラットフォーム互換性が重要な場合
  - デバッグ中または開発初期段階

- **共有メモリが適している場合**:
  - 大規模データの高速交換（数十MB以上）
  - 繰り返し実行による高いパフォーマンスが必要
  - プラグインが正しくインストールされている環境
  - 本番環境や最終実装

## サンプルコード

PyFreeFEM-MLには、ファイルIOを使用したサンプルコードが含まれています。

### ポアソン方程式サンプル

```python
# examples/file_io/file_io_wrapper.py の使用例
from pyfreefem_ml.file_io import FreeFEMFileIO

# インターフェース初期化
ff = FreeFEMFileIO(debug=True)

# スクリプト実行
success, solution, stdout, stderr = ff.run_script(
    'examples/file_io/poisson_file_io.edp'
)

if success:
    # 結果のプロット
    import matplotlib.pyplot as plt
    import numpy as np
    
    # メッシュサイズ（FreeFEMスクリプトと一致させる）
    n = 10
    solution_2d = solution.reshape((n+1, n+1))
    
    plt.figure(figsize=(10, 8))
    plt.pcolormesh(solution_2d, cmap='viridis')
    plt.colorbar(label='値')
    plt.title('ポアソン方程式の解')
    plt.savefig('poisson_solution.png')
    plt.show()
```

対応するFreeFEMスクリプト（`examples/file_io/poisson_file_io.edp`）は、ポアソン方程式を解いて結果をファイルに出力します。

## トラブルシューティング

### よくある問題と解決策

1. **FreeFEMスクリプトの実行エラー**
   - FreeFEMパスが正しく設定されているか確認
   - 作業ディレクトリがスクリプトからアクセス可能か確認
   - スクリプト内のファイル名が`run_script()`の引数と一致しているか確認

2. **データ形式の不一致**
   - FreeFEMとPython間のデータ型の一致を確認
   - 多次元配列を扱う場合はメタデータが正しいか確認
   - 数値精度（特に浮動小数点数）が適切か確認

3. **WSL環境での問題**
   - パスの変換が正しく行われているか確認
   - WSL環境のFreeFEMが実行可能か直接確認
   - ファイルアクセス権限の問題がないか確認

4. **大きなデータセットの処理**
   - 大きなデータの場合、バイナリ形式を検討（`numpy.save`/`numpy.load`）
   - メモリ使用量に注意し、必要に応じてデータを分割

### パフォーマンス改善のヒント

1. テキスト形式よりもバイナリ形式を使用する
2. データサイズが大きい場合は圧縮アルゴリズムを検討
3. 不要なデータは交換しない（事前にフィルタリング）
4. ディスクI/Oを最小限に抑えるため、交換頻度を減らす

## 最新の改善点（2024年3月）

### 統一インターフェースの導入

PyFreeFEM-MLでは、共有メモリとファイルIOの両方の機能を統一的に扱える`PyFreeFEM`クラスを導入しました：

```python
from pyfreefem_ml import PyFreeFEM

# 統一インターフェースを使用して初期化
ff = PyFreeFEM(
    wsl_mode=True,  # WSL環境を使用する場合はTrue
    debug=True      # デバッグモード
)

# スクリプト実行（共有メモリまたはファイルIOが自動選択される）
success, result, stdout, stderr = ff.run_script(
    script_path='script.edp',
    input_data=input_array,
    metadata_file='metadata.txt'  # 多次元配列用
)
```

### Windows+WSL環境での改善

Windows+WSL環境での実行時に以下の改善を行いました：

1. パス変換の自動化
   - WindowsパスからWSLパスへの自動変換
   - 一時ディレクトリの適切な管理

2. 多次元配列のサポート強化
   - メタデータファイルを使用した形状情報の保持
   - 2次元・3次元配列の自動変換

3. エラーハンドリングの改善
   - WSL固有のエラーに対する適切な処理
   - デバッグ情報の詳細な出力

### 使用例

```python
from pyfreefem_ml import PyFreeFEM
import numpy as np

# 2次元テストデータ作成
test_array = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

# 統一インターフェースを使用して初期化
ff = PyFreeFEM(
    wsl_mode=True,  # WSL環境を使用
    debug=True
)

# テスト実行
success, result, stdout, stderr = ff.run_script(
    script_path='multi_array_test.edp',
    input_data=test_array.flatten(),
    metadata_file='matrix_metadata.txt'
)

if success:
    print(f"出力配列: 形状={result.shape}, データ={result}")
else:
    print(f"エラー: {stderr}")
```

この改善により、以下の利点が得られます：

- プラットフォームに依存しない統一的なAPI
- Windows+WSL環境での安定した動作
- 多次元配列の扱いの簡素化
- デバッグのしやすさの向上

---

このガイドがPyFreeFEM-MLでのファイルIOによるデータ通信の理解の助けになれば幸いです。さらに詳細な情報や最新の機能については、公式ドキュメントを参照してください。 