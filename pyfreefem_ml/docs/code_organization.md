# PyFreeFEM コード構成

## ディレクトリ構造

プロジェクトのコードは以下のような構造に整理されています：

```
pj_TO_MLaSO_SIMP/
│
├── document/           # ドキュメント
│   ├── dev/            # 開発用ドキュメント
│   └── ...
│
├── src/                # ソースコード
│   ├── freefem/        # FreeFEM関連のコード
│   │   ├── libs/       # FreeFEMライブラリ
│   │   │   └── shm_comm.idp    # 共有メモリ通信ライブラリ
│   │   │
│   │   └── plugins/    # FreeFEMプラグイン
│   │       └── mmap-semaphore.cpp  # 共有メモリ操作プラグイン
│   │
│   └── pyfreefem/      # Pythonライブラリ
│       ├── __init__.py         # パッケージ初期化
│       ├── data_converter.py   # データ型変換
│       ├── errors.py           # 例外クラス
│       ├── freefem_interface.py # 高レベルAPI
│       ├── freefem_runner.py   # FreeFEM実行
│       ├── shm_manager.py      # 共有メモリ管理
│       │
│       └── other/              # その他の関連コード（メインではない）
│           ├── file_comm.py    # ファイルベース通信
│           ├── freefem_comm.py # ファイルベースFreeFEM通信
│           └── pyfreefem.py    # 古いPyFreeFEMモジュール
│
└── tests/              # テストコード
    ├── freefem/        # FreeFEM側テスト
    │   └── test_shm_comm.edp  # 共有メモリ通信テスト
    │
    └── python/         # Python側テスト
        ├── test_freefem_shm.py  # 共有メモリ通信テスト
        └── plot_test_result.py  # 結果可視化
```

## コアコンポーネント

### 1. Pythonライブラリ（`src/pyfreefem/`）

#### 核となるモジュール
- `shm_manager.py`: 共有メモリの低レベル操作を担当
- `freefem_interface.py`: 高レベルなユーザー向けAPI
- `freefem_runner.py`: FreeFEMスクリプトの実行管理
- `data_converter.py`: データ型変換ユーティリティ
- `errors.py`: 例外クラス定義

#### パッケージの使い方
```python
from pyfreefem import FreeFEMInterface

# インターフェースの初期化
ff = FreeFEMInterface(debug=True)

# データの設定
ff.write_array(np.array([1.0, 2.0, 3.0]), "input_data")

# FreeFEMスクリプトの実行
success, stdout, stderr = ff.run_script("my_script.edp")

# 結果の取得
result = ff.read_array("output_data", 0, (3,), np.float64)
```

### 2. FreeFEMコード（`src/freefem/`）

#### 共有メモリプラグイン
- `plugins/mmap-semaphore.cpp`: 共有メモリ操作のC++プラグイン

#### ヘルパーライブラリ
- `libs/shm_comm.idp`: FreeFEMから共有メモリを使いやすくするヘルパー関数

#### 使用例（FreeFEM側）
```
// ライブラリのインクルード
include "shm_comm.idp"

// 配列の宣言
real[int] data(5);

// 共有メモリからデータ読み込み
ReadRealArray(data, "input_data");

// 計算処理
for (int i = 0; i < data.n; i++)
    data[i] = data[i] * 2;

// 結果を共有メモリに書き込み
WriteRealArray(data, "output_data");
```

## その他のコンポーネント（`src/pyfreefem/other/`）

以下のコードは共有メモリ通信とは別のアプローチで、主にファイルベースの通信を実装したものです：

- `file_comm.py`: ファイルベースの通信マネージャー
- `freefem_comm.py`: ファイルベースのFreeFEM通信
- `pyfreefem.py`: 初期バージョンのPyFreeFEMモジュール

これらは今後の拡張や参照用として保持されていますが、現在の主要な実装は共有メモリベースのものです。

## テストコード

### FreeFEM側テスト
- `tests/freefem/test_shm_comm.edp`: 共有メモリ通信のFreeFEM側テスト

### Python側テスト
- `tests/python/test_freefem_shm.py`: 共有メモリ通信のPython側テスト
- `tests/python/plot_test_result.py`: テスト結果の可視化ツール

## 今後の開発

コードの構成は、より多くの機能を追加する際にも、以下の原則を維持します：

1. **関心の分離**: 共有メモリ管理、FreeFEM実行、データ変換など、機能ごとに分離
2. **レイヤー構造**: 低レベルAPI（`shm_manager.py`）と高レベルAPI（`freefem_interface.py`）の区別
3. **拡張性**: 新機能の追加が容易な構造
4. **テスト容易性**: 各コンポーネントを独立してテスト可能
5. **下位互換性**: APIの急激な変更を避け、既存コードへの影響を最小化 