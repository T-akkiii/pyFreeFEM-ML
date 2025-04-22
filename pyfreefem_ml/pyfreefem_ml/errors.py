"""
Python-FreeFEM共有データ通信ライブラリのエラー定義

FreeFEMとの連携時に発生する可能性のある例外クラスを定義します。
"""

class FreeFEMBaseError(Exception):
    """FreeFEM関連の基本エラークラス"""
    
    def __init__(self, message, details=None):
        """
        初期化
        
        Parameters
        ----------
        message : str
            エラーメッセージ
        details : dict, optional
            エラーの詳細情報
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
        
    def __str__(self):
        """エラーメッセージの文字列表現"""
        if not self.details:
            return self.message
            
        details_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
        return f"{self.message} ({details_str})"


class FreeFEMExecutionError(FreeFEMBaseError):
    """FreeFEMスクリプト実行中に発生したエラー"""
    
    def __init__(self, message, script_path=None, return_code=None, stderr=None):
        """
        初期化
        
        Parameters
        ----------
        message : str
            エラーメッセージ
        script_path : str, optional
            実行されたスクリプトのパス
        return_code : int, optional
            FreeFEMプロセスの終了コード
        stderr : str, optional
            標準エラー出力の内容
        """
        details = {
            'script_path': script_path,
            'return_code': return_code,
            'stderr': stderr
        }
        super().__init__(message, details)


class DataTransferError(FreeFEMBaseError):
    """データ転送中に発生したエラー"""
    
    def __init__(self, message, data_name=None, data_type=None, direction=None):
        """
        初期化
        
        Parameters
        ----------
        message : str
            エラーメッセージ
        data_name : str, optional
            処理中のデータ名
        data_type : str, optional
            データの型情報
        direction : str, optional
            転送方向 ('to_freefem' または 'from_freefem')
        """
        details = {
            'data_name': data_name,
            'data_type': data_type,
            'direction': direction
        }
        super().__init__(message, details)


class TimeoutError(FreeFEMBaseError):
    """処理がタイムアウトした場合のエラー"""
    
    def __init__(self, message, operation=None, timeout=None):
        """
        初期化
        
        Parameters
        ----------
        message : str
            エラーメッセージ
        operation : str, optional
            タイムアウトした操作の名前
        timeout : float, optional
            設定されていたタイムアウト時間（秒）
        """
        details = {
            'operation': operation,
            'timeout': timeout
        }
        super().__init__(message, details)


class FileOperationError(FreeFEMBaseError):
    """ファイル操作に関するエラー"""
    
    def __init__(self, message, file_path=None, operation=None):
        """
        初期化
        
        Parameters
        ----------
        message : str
            エラーメッセージ
        file_path : str, optional
            処理中のファイルパス
        operation : str, optional
            実行されていた操作 ('read', 'write', 'delete' など)
        """
        details = {
            'file_path': file_path,
            'operation': operation
        }
        super().__init__(message, details) 