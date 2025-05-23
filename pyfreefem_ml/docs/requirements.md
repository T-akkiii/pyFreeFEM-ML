理解しました。実装難易度を下げつつ明確な要件定義を行うため、以下のように整理し直します：

# Python-FreeFEM間共有メモリライブラリの実装指向要件定義

## 1. データ交換要件

### 1.1 対応データ型
- 整数値（int）: C言語のint型と互換性のある形式で格納
- 実数値（double）: C言語のdouble型と互換性のある形式で格納
- 整数配列（int[]）: 連続したメモリブロックとして格納、1次元および多次元（行優先形式）
- 実数配列（double[]）: 連続したメモリブロックとして格納、1次元および多次元（行優先形式）

### 1.2 データ構造設計
- 共有メモリ内でのデータ配置：[ヘッダ情報（データ型、サイズ）][実データ]
- 変数名と共有メモリアドレスのマッピングテーブルを管理
- 多次元配列は1次元に変換して格納（行優先）

## 2. 共有メモリ管理

### 2.1 共有メモリ確保・解放
- POSIX共有メモリ（shm_open/mmap）を使用
- 確保時に一意の識別子を生成（プロセスIDとタイムスタンプベース）
- シンプルな解放機構（unmap、shm_unlink）

### 2.2 同期機構
- セマフォは最小限（1つの共有セマフォ）で実装
- 書き込み/読み取り操作の前後でロック/アンロック
- 長時間のブロックを避けるための単純なタイムアウト機構

## 3. Python側インターフェース

### 3.1 基本クラス
- `SharedMemoryManager`: 低レベル共有メモリ操作
- `FreeFEMInterface`: 高レベルインターフェース（変数管理、スクリプト実行）

### 3.2 主要メソッド
- `write_variable(name, value)`: 変数書き込み
- `read_variable(name)`: 変数読み取り
- `run_script(script_path)`: FreeFEMスクリプト実行
- `cleanup()`: リソース解放

## 4. FreeFEM側プラグイン

### 4.1 プラグイン関数
- `ShmCreate(name, size)`: 共有メモリ作成
- `ShmDestroy(name)`: 共有メモリ解放
- `ShmWriteInt(name, value)`: 整数書き込み
- `ShmReadInt(name)`: 整数読み取り
- `ShmWriteDouble(name, value)`: 実数書き込み
- `ShmReadDouble(name)`: 実数読み取り
- `ShmWriteArray(name, array)`: 配列書き込み
- `ShmReadArray(name, array)`: 配列読み取り

### 4.2 プラグインのビルド・インストール
- 単一のCppファイルでの実装
- FreeFEMのプラグインビルド規約に従った実装
- Makefileを使用したシンプルなビルドプロセス

## 5. エラー処理

### 5.1 エラーパターン
- 共有メモリ確保失敗: システムエラーコードを伝達
- 型不一致エラー: データ型を検証し不一致時は明示的エラー
- タイムアウト: 一定時間後に操作を諦める
- FreeFEM実行エラー: 標準エラー出力をキャプチャして伝達

### 5.2 例外クラス
- `SharedMemoryError`: 共有メモリ操作に関するエラー
- `FreeFEMError`: FreeFEM実行に関するエラー
- `TimeoutError`: タイムアウト関連エラー

## 6. WSL2対応

### 6.1 パス変換
- Windows形式パスとWSL形式パスの自動変換機能
- 環境変数を使用したFreeFEMパスの指定機能

### 6.2 プロセス管理
- WSL内でのプロセス実行機能（subprocess使用）
- シンプルなストリーム管理（標準出力・標準エラー）

## 7. 最小限のテスト

### 7.1 基本テスト
- データ型ごとの書き込み・読み取りテスト
- エラー処理テスト
- WSL環境でのテスト

### 7.2 サンプルコード
- 基本的な使用例（数値計算）