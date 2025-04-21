# PyFreeFEM - Python-FreeFEM共有メモリ通信ライブラリ

このライブラリは、Python と FreeFEM 間でデータをやり取りするための共有メモリベースの通信機能を提供します。WSL環境でのFreeFEM 4.1の制約に対応し、シンプルかつ堅牢な通信機能を実現します。科学計算やシミュレーションの分野でPythonの利便性とFreeFEMの高度な有限要素計算能力を組み合わせることができます。

## 主な機能

- **PythonからFreeFEMコードの実行**: スクリプトの指定と実行、パラメータ設定、プロセス管理
- **共有メモリによるデータ転送**: ファイル不要の高速データ交換
- **様々なデータ型のサポート**: 整数、実数、文字列、配列などの基本的なデータ型
- **WSL環境対応**: Windows上のPythonとWSL内のFreeFEMとの連携
- **エラー処理**: 詳細なエラー報告と例外によるエラー処理
- **シンプルなAPI**: 変数名ベースのデータアクセスと高レベルインターフェース

## インストール方法

```bash
# リポジトリのクローン
git clone https://github.com/your-username/pyfreefem.git
cd pyfreefem

# インストール
pip install -e .
```

## 使い方

### 基本的な使い方

```python
from pyfreefem import FreeFEMInterface

# FreeFEMインターフェースの初期化
ff = FreeFEMInterface(shm_size=1024*1024, wsl_mode=True)

# データの設定
ff.set_data("scalar_int", 42)           # 整数値の書き込み
ff.set_data("scalar_double", 3.14159)   # 浮動小数点値の書き込み
ff.set_data("array_data", [1.0, 2.0, 3.0])  # 配列の書き込み

# FreeFEMスクリプトの実行
script_path = "path/to/your/script.edp"
result = ff.run_script(script_path)

# 結果の取得
result_int = ff.get_data("result_int")
result_double = ff.get_data("result_double")
result_array = ff.get_data("result_array")

# 後片付け
ff.cleanup()
```

### 実践的な例

例示スクリプト `examples/basic_usage.py` から抜粋:

```python
# PyFreeFEMインスタンスを作成
pff = PyFreeFEM(freefem_path="FreeFem++")
    
# セッションを開始
session_id = pff.start_session()
    
# 変数をPythonから共有メモリに書き込む
pff.write_variable("scalar_int", 42)
pff.write_variable("scalar_float", 3.14159)
    
# NumPy配列を書き込む
matrix = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64)
pff.write_variable("matrix", matrix)
    
# FreeFEMスクリプトを実行
return_code, stdout, stderr = pff.run_script(script)
    
# FreeFEMからの結果を読み込む
matrix_sum = pff.read_variable("matrix_sum")
pi_squared = pff.read_variable("pi_squared")
```

### FreeFEM側のコード例

```
// 共有メモリプラグインをロード
load "mmap-semaphore"

// 環境変数から共有メモリ情報を取得
string shm_name = getenv("FF_SHM_NAME");
int shm_size = atoi(getenv("FF_SHM_SIZE"));

// 共有メモリ初期化
createSharedMemory(shm_name, shm_size);

// 整数値の読み取り
int scalar_int;
GetFromMmap(shm, "scalar_int", scalar_int);
log("整数値を読み込みました: " + scalar_int);

// 何らかの処理を実行
scalar_int += 10;

// 処理結果を書き込み
SetInMmap(shm, "result_int", scalar_int);
```

## ライブラリの構成

PyFreeFEMは以下の主要コンポーネントで構成されています:

### SharedMemoryManager

低レベルの共有メモリ操作を担当するクラスです。

```python
from pyfreefem.shm_manager import SharedMemoryManager

# 初期化
shm = SharedMemoryManager("shm_name", 1024*1024)

# データ操作
shm.write_int(0, 42)            # インデックス0に整数値を書き込み
shm.write_double(1, 3.14159)    # インデックス1に浮動小数点値を書き込み
shm.write_string(2, "Hello")    # インデックス2に文字列を書き込み

val_int = shm.read_int(0)       # 整数値の読み取り
val_double = shm.read_double(1) # 浮動小数点値の読み取り
val_str = shm.read_string(2)    # 文字列の読み取り

# 後片付け
shm.cleanup()
```

### FreeFEMInterface

高レベルの操作を提供するクラスです。共有メモリの管理とFreeFEMスクリプトの実行を統合します。

```python
from pyfreefem.freefem_interface import FreeFEMInterface

# 初期化
ff = FreeFEMInterface()

# 変数の設定と取得 (名前付き)
ff.set_data("my_int", 42)
ff.set_data("pi", 3.14159)
ff.set_data("array1", [1, 2, 3])

# スクリプト実行
result = ff.run_script("script.edp")

# 結果取得
result = ff.get_data("result")
matrix = ff.get_data("matrix")

# 後片付け
ff.cleanup()
```

### FreeFEMRunner

FreeFEMプロセスの実行と管理を担当するクラスです。

```python
from pyfreefem.freefem_runner import FreeFEMRunner

# 初期化
runner = FreeFEMRunner(freefem_path="FreeFem++", wsl_mode=True)

# スクリプト実行
result = runner.run("script.edp", timeout=30)

# 結果確認
if result.success:
    print(f"出力: {result.output}")
else:
    print(f"エラー: {result.error}")
```

### データ変換ユーティリティ

Python型とFreeFEM型の相互変換を担当する機能です。

```python
from pyfreefem.data_converter import convert_to_freefem, convert_from_freefem

# Pythonデータの変換
freefem_data = convert_to_freefem(42, "int")

# FreeFEMデータの変換
python_data = convert_from_freefem(freefem_data, "int")
```

## テスト済み機能

このライブラリには以下のテストが実装されており、機能の動作が確認されています:

1. **基本機能テスト** (`tests/test_pyfreefem.py`)
   - 基本データ型の書き込みと読み込み
   - 整数値、浮動小数点値、文字列、配列のテスト
   - FreeFEMスクリプト実行

2. **共有メモリテスト** (`tests/test_simple_shm.py` および `.edp`)
   - 共有メモリの初期化
   - データの書き込みと読み込み
   - 同期メカニズムのテスト

## 技術的詳細

### 共有メモリの仕組み

このライブラリは、POSIXの共有メモリ (mmap) とセマフォを使用してPythonとFreeFEM間でデータを交換します。FreeFEM側ではC++で実装されたプラグインを使用して共有メモリにアクセスします。

### データ型の変換

| Python型 | 共有メモリ内の表現 | FreeFEM型 |
|----------|-------------------|-----------|
| int      | 整数値             | int       |
| float    | 浮動小数点値        | real      |
| str      | 文字列             | string    |
| ndarray  | 一連の浮動小数点値  | real[int] |

### エラーハンドリング

各操作は適切なエラーコードを返し、問題が発生した場合は例外を発生させます。主な例外クラスは次のとおりです：

- `FreeFEMBaseError`: 基本エラークラス
- `FreeFEMExecutionError`: FreeFEMスクリプトの実行エラー
- `DataTransferError`: データ転送中のエラー
- `TimeoutError`: タイムアウトエラー
- `FileOperationError`: ファイル操作エラー

## トラブルシューティング

### 共有メモリが解放されない場合

```python
# 強制的に共有メモリを解放
from pyfreefem.shm_manager import SharedMemoryManager
SharedMemoryManager.force_cleanup("shm_name")
```

### WSL環境での問題

WSL環境では、パスの変換が適切に行われていることを確認してください。また、FreeFEMが適切にインストールされ、パスが通っていることを確認してください。

### よくあるエラーと解決方法

- **共有メモリアクセスエラー**: ライブラリの `.cleanup()` メソッドが呼ばれていない可能性があります。
- **FreeFEM実行エラー**: FreeFEMのパスが正しく設定されているか確認してください。
- **WSLパス変換エラー**: WSLモードが正しく設定されているか確認してください。

## ライセンス

MITライセンスの下で公開されています。詳細はLICENSEファイルを参照してください。 