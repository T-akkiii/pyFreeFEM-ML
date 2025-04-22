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

## プロジェクト構造

```
pyfreefem_ml/          # メインパッケージディレクトリ
├── pyfreefem_ml/      # Pythonパッケージのソースコード
├── plugins/           # FreeFEMプラグイン
├── examples/          # 使用例
├── tests/             # テスト
├── docs/              # ドキュメント
├── setup.py           # インストール設定
└── README.md          # パッケージの説明
```

詳細な構造と使用方法については、パッケージディレクトリ内のREADMEを参照してください。

## インストール方法

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/pyfreefem-ml.git
cd pyfreefem-ml

# パッケージとFreeFEMプラグインのインストール
pip install -e pyfreefem_ml
```

## ライセンス

MIT License 