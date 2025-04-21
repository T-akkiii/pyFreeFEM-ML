#!/usr/bin/env python3
"""
トポロジー最適化の例

Python-FreeFEM共有データ通信ライブラリを使用して、
トポロジー最適化問題を解くサンプルスクリプトです。
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ライブラリのパスを追加
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pyfreefem.freefem_comm import FreeFEMComm
from pyfreefem.errors import FreeFEMExecutionError, DataTransferError

# トポロジー最適化のパラメータ
class OptimizationParams:
    def __init__(self):
        self.max_iter = 50          # 最大反復回数
        self.nelx = 60              # x方向要素数
        self.nely = 30              # y方向要素数
        self.volfrac = 0.4          # 体積制約
        self.penal = 3.0            # ペナルティパラメータ
        self.rmin = 1.5             # フィルタ半径
        self.change_threshold = 0.01  # 収束判定の閾値

def run_topo_optimization():
    """
    トポロジー最適化の実行
    """
    print("トポロジー最適化を開始します...")
    
    # パラメータの設定
    params = OptimizationParams()
    
    # FreeFEM通信マネージャーの作成
    comm = FreeFEMComm(verbose=True)
    
    # FreeFEMスクリプトのパス
    script_dir = current_dir.parent / "freefem"
    topo_script = script_dir / "topo_opt_file_shm.edp"
    
    if not topo_script.exists():
        print(f"エラー: スクリプトファイルが見つかりません: {topo_script}")
        return False
    
    # 初期密度場の設定（体積制約に一致する一様場）
    nelx, nely = params.nelx, params.nely
    density = np.ones((nely, nelx)) * params.volfrac
    
    # 最適化パラメータをFreeFEMに設定
    comm.set_data("nelx", nelx)
    comm.set_data("nely", nely)
    comm.set_data("volfrac", params.volfrac)
    comm.set_data("penal", params.penal)
    comm.set_data("rmin", params.rmin)
    comm.set_data("density", density.flatten())  # 密度場（1次元配列に変換）
    
    # 結果の保存ディレクトリ
    result_dir = Path("./results")
    result_dir.mkdir(exist_ok=True)
    
    # 最適化のメインループ
    iterations = []
    compliances = []
    volumes = []
    
    try:
        for iter_num in range(params.max_iter):
            print(f"\n反復 {iter_num+1}/{params.max_iter}")
            
            # FreeFEMスクリプトを実行
            result = comm.run_script(
                script_path=str(topo_script),
                parameters={
                    "iter": iter_num,
                    "result_dir": str(result_dir)
                }
            )
            
            if not result["success"]:
                print("FreeFEMスクリプトの実行に失敗しました")
                print(f"エラー: {result['error']}")
                return False
            
            # 結果を取得
            compliance = comm.extract_script_result(result["output"], variable_name="compliance")
            volume = comm.extract_script_result(result["output"], variable_name="volume")
            
            # 新しい密度場を取得
            new_density = comm.get_data("density")
            
            if new_density is not None:
                new_density = np.array(new_density).reshape((nely, nelx))
                
                # 密度場の変化を計算
                change = np.abs(new_density - density).max()
                density = new_density
                
                # 結果を表示
                print(f"コンプライアンス: {compliance:.4f}")
                print(f"体積比: {volume:.4f}")
                print(f"最大変化量: {change:.4f}")
                
                # 結果を保存
                iterations.append(iter_num + 1)
                compliances.append(compliance)
                volumes.append(volume)
                
                # 密度場を可視化
                if (iter_num + 1) % 5 == 0 or iter_num == 0 or iter_num == params.max_iter - 1:
                    plt.figure(figsize=(10, 5))
                    plt.imshow(density, cmap='gray', interpolation='none')
                    plt.colorbar()
                    plt.title(f"密度分布 (反復 {iter_num+1})")
                    plt.savefig(result_dir / f"density_{iter_num+1:03d}.png")
                    plt.close()
                
                # 収束判定
                if change < params.change_threshold:
                    print(f"\n収束しました (反復 {iter_num+1})")
                    break
            else:
                print("警告: 密度データを取得できませんでした")
                
    except KeyboardInterrupt:
        print("\n最適化を中断しました")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return False
    finally:
        # 最適化結果のプロット
        plot_optimization_results(iterations, compliances, volumes, result_dir)
        
        # 最終結果の保存
        np.savetxt(result_dir / "final_density.txt", density)
        
        # リソースのクリーンアップ
        comm.cleanup()
    
    print("\nトポロジー最適化が完了しました")
    return True

def plot_optimization_results(iterations, compliances, volumes, result_dir):
    """
    最適化結果をプロット
    
    Parameters
    ----------
    iterations : list
        反復回数のリスト
    compliances : list
        各反復のコンプライアンス値
    volumes : list
        各反復の体積比
    result_dir : Path
        結果を保存するディレクトリ
    """
    if not iterations:
        return
    
    # コンプライアンスの推移
    plt.figure(figsize=(10, 6))
    plt.plot(iterations, compliances, 'b-', lw=2)
    plt.xlabel('反復回数')
    plt.ylabel('コンプライアンス')
    plt.title('コンプライアンスの推移')
    plt.grid(True)
    plt.savefig(result_dir / "compliance_history.png")
    plt.close()
    
    # 体積比の推移
    plt.figure(figsize=(10, 6))
    plt.plot(iterations, volumes, 'r-', lw=2)
    plt.axhline(y=0.4, color='k', linestyle='--', label='目標体積比')
    plt.xlabel('反復回数')
    plt.ylabel('体積比')
    plt.title('体積比の推移')
    plt.grid(True)
    plt.legend()
    plt.savefig(result_dir / "volume_history.png")
    plt.close()
    
    # 両方のグラフを１つの画像に
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(iterations, compliances, 'b-', lw=2)
    plt.ylabel('コンプライアンス')
    plt.title('最適化の推移')
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(iterations, volumes, 'r-', lw=2)
    plt.axhline(y=0.4, color='k', linestyle='--', label='目標体積比')
    plt.xlabel('反復回数')
    plt.ylabel('体積比')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(result_dir / "optimization_history.png")
    plt.close()
    
    # 結果をCSVとして保存
    import pandas as pd
    df = pd.DataFrame({
        '反復回数': iterations,
        'コンプライアンス': compliances,
        '体積比': volumes
    })
    df.to_csv(result_dir / "optimization_results.csv", index=False)

if __name__ == "__main__":
    run_topo_optimization() 