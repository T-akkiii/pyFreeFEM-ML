#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PyFreeFEMデータ変換モジュール

Python形式のデータをFreeFEM形式に変換するユーティリティ関数を提供します。
また、FreeFEM形式のデータをPython形式に変換する関数も含まれています。
"""

import json
import numpy as np
import re
from .errors import DataTransferError

def convert_to_freefem(data, data_name=None):
    """
    PythonデータをFreeFEM文字列形式に変換する
    
    Parameters
    ----------
    data : object
        変換するPythonデータ（スカラー、リスト、タプル、NumPy配列など）
    data_name : str, optional
        データの名前（エラー報告用）
        
    Returns
    -------
    str
        FreeFEM形式の文字列表現
    
    Raises
    ------
    DataTransferError
        サポートされていないデータ型の場合
    """
    try:
        # 単一値の場合
        if isinstance(data, (int, float)):
            return str(data)
        
        # ブール値の場合
        if isinstance(data, bool):
            return 'true' if data else 'false'
        
        # 文字列の場合
        if isinstance(data, str):
            # FreeFEMではシングルクォートを使用
            return f"'{data}'"
        
        # リスト/タプルの場合
        if isinstance(data, (list, tuple)):
            # FreeFEM形式は [n](a, b, c, ...)
            elements = ", ".join([convert_to_freefem(elem) for elem in data])
            return f"[{len(data)}]({elements})"
        
        # NumPy配列の場合
        if isinstance(data, np.ndarray):
            if data.ndim == 1:
                # 1次元配列
                elements = ", ".join([str(elem) for elem in data])
                return f"[{len(data)}]({elements})"
            elif data.ndim == 2:
                # 2次元配列（FreeFEMの行列形式）
                rows, cols = data.shape
                matrix_str = "["
                for i in range(rows):
                    row_str = ", ".join([str(data[i, j]) for j in range(cols)])
                    matrix_str += f"[{cols}]({row_str})"
                    if i < rows - 1:
                        matrix_str += ", "
                matrix_str += "]"
                return matrix_str
            else:
                # 高次元配列はサポート外
                raise DataTransferError(
                    f"FreeFEMは{data.ndim}次元配列をサポートしていません",
                    data_name=data_name,
                    data_type=type(data).__name__,
                    direction='to_freefem'
                )
        
        # その他のオブジェクトは文字列に変換
        return str(data)
        
    except Exception as e:
        # 変換中のその他のエラー
        if isinstance(e, DataTransferError):
            raise
        raise DataTransferError(
            f"データ変換エラー: {str(e)}",
            data_name=data_name,
            data_type=type(data).__name__,
            direction='to_freefem'
        ) from e


def convert_from_freefem(freefem_str, dtype=None, data_name=None):
    """
    FreeFEM文字列形式をPythonオブジェクトに変換する
    
    Parameters
    ----------
    freefem_str : str
        FreeFEM形式の文字列（[n](a, b, c, ...)など）
    dtype : type, optional
        変換後のデータ型。指定がない場合は自動判定
    data_name : str, optional
        データの名前（エラー報告用）
        
    Returns
    -------
    object
        変換されたPythonオブジェクト
    
    Raises
    ------
    DataTransferError
        データの解析に失敗した場合
    """
    try:
        # 空文字列の場合
        if not freefem_str or freefem_str.strip() == '':
            return None
        
        # ブール値の場合
        if freefem_str.lower() == 'true':
            return True
        if freefem_str.lower() == 'false':
            return False
        
        # 配列表記 [n](a, b, c, ...) の場合
        array_pattern = r'\[(\d+)\]\((.*)\)'
        match = re.match(array_pattern, freefem_str.strip())
        if match:
            size = int(match.group(1))
            content = match.group(2)
            
            # カンマで分割し、再帰的に各要素を変換
            elements = []
            # カンマを単純に分割すると括弧内のカンマも分割してしまうため、括弧のレベルを追跡
            level = 0
            current = ''
            for char in content:
                if char == '(' or char == '[':
                    level += 1
                    current += char
                elif char == ')' or char == ']':
                    level -= 1
                    current += char
                elif char == ',' and level == 0:
                    elements.append(convert_from_freefem(current.strip()))
                    current = ''
                else:
                    current += char
            
            # 最後の要素
            if current.strip():
                elements.append(convert_from_freefem(current.strip()))
            
            # 要素数が一致するか確認
            if len(elements) != size:
                print(f"警告: 配列サイズ不一致 (宣言: {size}, 実際: {len(elements)})")
            
            # データ型の変換
            if dtype:
                if dtype == int:
                    elements = [int(e) for e in elements]
                elif dtype == float:
                    elements = [float(e) for e in elements]
                elif dtype == np.ndarray:
                    elements = np.array(elements)
            
            return elements
        
        # 2次元配列の場合（ネストした[n](...)形式）
        matrix_pattern = r'\[(.*)\]'
        match = re.match(matrix_pattern, freefem_str.strip())
        if match and '[' in match.group(1) and ']' in match.group(1):
            content = match.group(1)
            rows = []
            
            # 行ごとに分割し処理
            level = 0
            current = ''
            for char in content:
                if char == '[':
                    if level == 0 and current.strip():
                        # 新しい行の開始
                        current = char
                    else:
                        current += char
                    level += 1
                elif char == ']':
                    level -= 1
                    current += char
                    if level == 0:
                        # 行の終了
                        rows.append(convert_from_freefem(current.strip()))
                        current = ''
                elif char == ',' and level == 0:
                    # 行の区切り
                    if current.strip():
                        rows.append(convert_from_freefem(current.strip()))
                        current = ''
                else:
                    current += char
            
            # 最後の行
            if current.strip():
                rows.append(convert_from_freefem(current.strip()))
            
            # NumPy配列に変換
            if dtype == np.ndarray or (dtype is None and all(isinstance(row, list) for row in rows)):
                # すべての行の長さが等しいことを確認
                if len(set(len(row) for row in rows)) != 1:
                    print("警告: 行の長さが一致しません")
                return np.array(rows)
            
            return rows
        
        # 数値の場合
        try:
            # 整数として解釈できる場合
            if '.' not in freefem_str and 'e' not in freefem_str.lower():
                return int(freefem_str)
            # 浮動小数点数として解釈
            return float(freefem_str)
        except ValueError:
            # 数値ではない場合、文字列として返す
            # FreeFEMの文字列はシングルクォートで囲まれている
            if freefem_str.startswith("'") and freefem_str.endswith("'"):
                return freefem_str[1:-1]
            return freefem_str
        
    except Exception as e:
        # 変換中のエラー
        if isinstance(e, DataTransferError):
            raise
        raise DataTransferError(
            f"データ解析エラー: {str(e)}",
            data_name=data_name,
            direction='from_freefem'
        ) from e 