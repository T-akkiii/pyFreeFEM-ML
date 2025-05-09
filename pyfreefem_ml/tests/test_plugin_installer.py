#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FreeFEMプラグインインストーラーのテスト
"""

import os
import sys
import unittest
from unittest import mock
import tempfile
from pathlib import Path

# プロジェクトルートへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyfreefem_ml.plugin_installer import PluginInstaller, install_plugin

class TestPluginInstaller(unittest.TestCase):
    """プラグインインストーラーのテストケース"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        # デバッグモードを有効化
        self.installer = PluginInstaller(debug=True)
    
    def test_wsl_detection(self):
        """WSL環境の検出機能をテスト"""
        # 元のメソッドを退避
        original_check_wsl = self.installer._check_wsl
        
        # 強制的にWSLありに設定
        self.installer._check_wsl = lambda: True
        self.assertTrue(self.installer.is_wsl)
        
        # 強制的にWSLなしに設定
        self.installer._check_wsl = lambda: False
        self.installer.__init__(debug=True)  # 再初期化
        self.assertFalse(self.installer.is_wsl)
        
        # 元に戻す
        self.installer._check_wsl = original_check_wsl
    
    @mock.patch('subprocess.run')
    def test_check_plugin_installation(self, mock_run):
        """プラグインのインストール状態チェック機能をテスト"""
        # インストール済みの場合
        mock_run.return_value = mock.Mock(returncode=0)
        self.installer.is_wsl = True
        self.assertTrue(self.installer.check_plugin_installation())
        
        # インストールされていない場合
        mock_run.side_effect = Exception("Command failed")
        self.assertFalse(self.installer.check_plugin_installation())
        
        # 非WSL環境でのテスト
        self.installer.is_wsl = False
        with mock.patch('os.path.isfile', return_value=True):
            self.assertTrue(self.installer.check_plugin_installation())
        
        with mock.patch('os.path.isfile', return_value=False):
            self.assertFalse(self.installer.check_plugin_installation())
    
    @mock.patch('pyfreefem_ml.plugin_installer.PluginInstaller.check_plugin_installation')
    @mock.patch('pyfreefem_ml.plugin_installer.PluginInstaller.install_plugin')
    @mock.patch('pyfreefem_ml.plugin_installer.PluginInstaller.setup_environment')
    def test_install_plugin_function(self, mock_setup_env, mock_install, mock_check):
        """install_plugin関数のテスト"""
        # プラグインが既にインストールされている場合
        mock_check.return_value = True
        self.assertTrue(install_plugin(debug=True))
        mock_install.assert_not_called()
        mock_setup_env.assert_called_once()
        
        # リセット
        mock_setup_env.reset_mock()
        
        # プラグインがインストールされていない場合
        mock_check.return_value = False
        mock_install.return_value = True
        self.assertTrue(install_plugin(debug=True))
        mock_install.assert_called_once()
        mock_setup_env.assert_called_once()
        
        # リセット
        mock_install.reset_mock()
        mock_setup_env.reset_mock()
        
        # インストールに失敗する場合
        mock_install.return_value = False
        self.assertFalse(install_plugin(debug=True))
        mock_install.assert_called_once()
        mock_setup_env.assert_not_called()
    
    def test_path_conversion(self):
        """WindowsパスからWSLパスへの変換をテスト"""
        # Windows環境でのみテスト
        if sys.platform.startswith('win'):
            # テスト用のWindowsパス
            win_path = Path("C:\\Users\\test\\Documents\\test.txt")
            
            # パス変換のモック
            with mock.patch('pathlib.Path.resolve', return_value=win_path):
                # 変換結果をチェック
                wsl_path = self.installer._convert_to_wsl_path(win_path)
                self.assertEqual(wsl_path, "/mnt/c/Users/test/Documents/test.txt")
    
    def test_setup_environment(self):
        """環境変数設定機能をテスト"""
        # 環境変数の元の値を保存
        original_env = os.environ.copy()
        
        # WSL環境の場合
        self.installer.is_wsl = True
        with mock.patch('subprocess.run', return_value=mock.Mock(returncode=0)):
            env_vars = self.installer.setup_environment()
            self.assertIn("FF_LOADPATH", env_vars)
            self.assertIn("FF_INCLUDEPATH", env_vars)
        
        # 非WSL環境の場合
        self.installer.is_wsl = False
        with mock.patch('os.path.isfile', return_value=True):
            env_vars = self.installer.setup_environment()
            self.assertIn("FF_LOADPATH", env_vars)
            self.assertIn("FF_INCLUDEPATH", env_vars)
        
        # 環境変数を元に戻す
        os.environ.clear()
        os.environ.update(original_env)

if __name__ == "__main__":
    unittest.main() 