#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ベクトル場データのFreeFEMとPython間の連携と可視化例

このスクリプトでは、FreeFEMでベクトル場を計算し、
Pythonで読み込んで可視化する方法を示します。
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import logging
from time import time

# パスを追加して親ディレクトリのモジュールをインポートできるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyfreefem_mlモジュールをインポート
from pyfreefem_ml import FreeFEMInterface

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('vector_field_example')

def sine_wave_vector_field(ff):
    """Sin波によるベクトル場の生成と可視化"""
    logger.info("==== Sin波ベクトル場の例 ====")
    
    # FreeFEMスクリプトでSin波のベクトル場を計算
    script = """
    load "mmap-semaphore"
    
    // メッシュ作成
    mesh Th = square(20, 20, [2*x-1, 2*y-1]);  // [-1,1]x[-1,1]の正方形領域
    
    // 関数空間定義
    fespace Vh(Th, P1);
    Vh u, v;  // x方向とy方向の成分
    
    // ベクトル場の定義（正弦波パターン）
    u = sin(pi*x) * cos(pi*y);
    v = -cos(pi*x) * sin(pi*y);
    
    // 格子点データの作成
    int nx = 20;
    int ny = 20;
    real[int] x_coords(nx*ny);
    real[int] y_coords(nx*ny);
    real[int] u_values(nx*ny);
    real[int] v_values(nx*ny);
    
    // 均等な格子点で値をサンプリング
    real dx = 2.0 / (nx - 1);  // [-1,1]の範囲で
    real dy = 2.0 / (ny - 1);
    
    int idx = 0;
    for (int j = 0; j < ny; j++) {
        for (int i = 0; i < nx; i++) {
            real x_val = -1.0 + i * dx;
            real y_val = -1.0 + j * dy;
            
            x_coords[idx] = x_val;
            y_coords[idx] = y_val;
            
            // 最も近い頂点での値を取得
            u_values[idx] = u(x_val, y_val);
            v_values[idx] = v(x_val, y_val);
            
            idx++;
        }
    }
    
    // データを共有メモリに書き込み
    ShmWriteArray("x_coords", x_coords, ArrayInfo(nx*ny, 0));
    ShmWriteArray("y_coords", y_coords, ArrayInfo(nx*ny, 0));
    ShmWriteArray("u_values", u_values, ArrayInfo(nx*ny, 0));
    ShmWriteArray("v_values", v_values, ArrayInfo(nx*ny, 0));
    
    // グリッドサイズ情報を書き込み
    ShmWriteInt("grid_nx", 0, nx);
    ShmWriteInt("grid_ny", 0, ny);
    
    cout << "ベクトル場データを共有メモリに書き込みました" << endl;
    """
    
    # スクリプトを実行
    logger.info("FreeFEMでベクトル場を計算中...")
    result = ff.run_inline_script(script)
    if not result[0]:
        logger.error(f"スクリプト実行エラー: {result[2]}")
        return False
    
    logger.info(f"スクリプト出力:\n{result[1]}")
    
    # グリッドサイズを取得
    nx = ff.read_int("grid_nx")
    ny = ff.read_int("grid_ny")
    logger.info(f"グリッドサイズ: {nx}x{ny}")
    
    # 座標と値を取得
    x_coords = ff.read_array("x_coords")
    y_coords = ff.read_array("y_coords")
    u_values = ff.read_array("u_values")
    v_values = ff.read_array("v_values")
    
    # グリッド形式に変換
    X = x_coords.reshape(ny, nx)
    Y = y_coords.reshape(ny, nx)
    U = u_values.reshape(ny, nx)
    V = v_values.reshape(ny, nx)
    
    # ベクトル場の可視化
    plt.figure(figsize=(10, 8))
    
    # ベクトル場をプロット
    Q = plt.quiver(X, Y, U, V, scale=25)
    plt.quiverkey(Q, 0.9, 0.9, 1, r'$1$', labelpos='E', coordinates='figure')
    
    # ベクトル場の大きさをカラーマップで表示
    magnitude = np.sqrt(U**2 + V**2)
    plt.pcolormesh(X, Y, magnitude, shading='auto', cmap='viridis', alpha=0.5)
    plt.colorbar(label='ベクトル場の大きさ')
    
    # グラフの設定
    plt.title('正弦波パターンのベクトル場')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.grid(True)
    plt.axis('equal')
    
    # 画像を保存
    plt.savefig('sine_wave_vector_field.png', dpi=300, bbox_inches='tight')
    logger.info("ベクトル場の可視化を 'sine_wave_vector_field.png' に保存しました")
    
    # プロットを表示
    plt.show()
    
    return True

def potential_flow_around_cylinder(ff):
    """円柱周りのポテンシャル流れの計算と可視化"""
    logger.info("==== 円柱周りのポテンシャル流れ ====")
    
    # FreeFEMスクリプトでポテンシャル流れを計算
    script = """
    load "mmap-semaphore"
    
    // 円柱周りの領域を作成
    real radius = 1.0;  // 円柱の半径
    real domainSize = 10.0;  // 外側境界までの距離
    border Circle(t=0, 2*pi) { x=radius*cos(t); y=radius*sin(t); }
    border Square(t=0, 4) {
        if (t < 1) { x=t*domainSize-domainSize/2; y=-domainSize/2; }
        else if (t < 2) { x=domainSize/2; y=(t-1)*domainSize-domainSize/2; }
        else if (t < 3) { x=domainSize/2-(t-2)*domainSize; y=domainSize/2; }
        else { x=-domainSize/2; y=domainSize/2-(t-3)*domainSize; }
    }
    
    // メッシュ生成
    int circlePoints = 50;
    int squarePoints = 25;
    mesh Th = buildmesh(Circle(circlePoints) + Square(squarePoints));
    
    // 関数空間の定義
    fespace Vh(Th, P2);
    Vh phi, psi;
    Vh vx, vy;
    
    // ラプラス方程式を解く（ポテンシャル流）
    // 境界条件: 円筒上での流れなし、遠方での一様流
    problem PotentialFlow(phi, psi) = 
        int2d(Th)(dx(phi)*dx(psi) + dy(phi)*dy(psi))
        + on(Circle, phi=0)
        + on(Square, phi=y);  // 左から右への一様流
    
    // ソルバーを実行
    PotentialFlow;
    
    // 速度場を計算（ポテンシャルの勾配）
    vx = dy(phi);
    vy = -dx(phi);
    
    // 均等グリッド上でのデータをサンプリング
    int nx = 50;
    int ny = 50;
    real dx = domainSize / (nx - 1);
    real dy = domainSize / (ny - 1);
    
    // 結果を格納する配列
    real[int] x_coords(nx*ny);
    real[int] y_coords(nx*ny);
    real[int] vx_values(nx*ny);
    real[int] vy_values(nx*ny);
    real[int] speed_values(nx*ny);
    
    // グリッド上でのデータをサンプリング
    int idx = 0;
    for (int j = 0; j < ny; j++) {
        for (int i = 0; i < nx; i++) {
            real x_val = -domainSize/2 + i * dx;
            real y_val = -domainSize/2 + j * dy;
            
            // 円柱内部のポイントはスキップ
            if (x_val*x_val + y_val*y_val <= radius*radius) {
                x_coords[idx] = x_val;
                y_coords[idx] = y_val;
                vx_values[idx] = 0;
                vy_values[idx] = 0;
                speed_values[idx] = 0;
            } else {
                x_coords[idx] = x_val;
                y_coords[idx] = y_val;
                vx_values[idx] = vx(x_val, y_val);
                vy_values[idx] = vy(x_val, y_val);
                speed_values[idx] = sqrt(vx_values[idx]^2 + vy_values[idx]^2);
            }
            idx++;
        }
    }
    
    // データを共有メモリに書き込み
    ShmWriteArray("cylinder_x_coords", x_coords, ArrayInfo(nx*ny, 0));
    ShmWriteArray("cylinder_y_coords", y_coords, ArrayInfo(nx*ny, 0));
    ShmWriteArray("cylinder_vx", vx_values, ArrayInfo(nx*ny, 0));
    ShmWriteArray("cylinder_vy", vy_values, ArrayInfo(nx*ny, 0));
    ShmWriteArray("cylinder_speed", speed_values, ArrayInfo(nx*ny, 0));
    
    // グリッドサイズ情報を書き込み
    ShmWriteInt("cylinder_nx", 0, nx);
    ShmWriteInt("cylinder_ny", 0, ny);
    ShmWriteDouble("cylinder_radius", 0, radius);
    
    cout << "円柱周りのポテンシャル流れデータを共有メモリに書き込みました" << endl;
    """
    
    # スクリプトを実行
    logger.info("FreeFEMでポテンシャル流れを計算中...")
    start_time = time()
    result = ff.run_inline_script(script)
    end_time = time()
    if not result[0]:
        logger.error(f"スクリプト実行エラー: {result[2]}")
        return False
    
    logger.info(f"計算時間: {end_time - start_time:.2f}秒")
    logger.info(f"スクリプト出力:\n{result[1]}")
    
    # グリッドサイズを取得
    nx = ff.read_int("cylinder_nx")
    ny = ff.read_int("cylinder_ny")
    radius = ff.read_double("cylinder_radius")
    logger.info(f"グリッドサイズ: {nx}x{ny}, 円柱半径: {radius}")
    
    # データを読み込み
    x_coords = ff.read_array("cylinder_x_coords")
    y_coords = ff.read_array("cylinder_y_coords")
    vx = ff.read_array("cylinder_vx")
    vy = ff.read_array("cylinder_vy")
    speed = ff.read_array("cylinder_speed")
    
    # グリッド形式に変換
    X = x_coords.reshape(ny, nx)
    Y = y_coords.reshape(ny, nx)
    VX = vx.reshape(ny, nx)
    VY = vy.reshape(ny, nx)
    SPEED = speed.reshape(ny, nx)
    
    # 可視化
    plt.figure(figsize=(12, 10))
    
    # 流れ場の大きさをカラーマップで表示
    contour = plt.contourf(X, Y, SPEED, 50, cmap='viridis')
    plt.colorbar(contour, label='流速')
    
    # ベクトル場を表示（間引いて表示）
    skip = 2
    Q = plt.quiver(X[::skip, ::skip], Y[::skip, ::skip], 
                   VX[::skip, ::skip], VY[::skip, ::skip], 
                   scale=50, width=0.002)
    plt.quiverkey(Q, 0.9, 0.9, 1, r'$1$', labelpos='E', coordinates='figure')
    
    # 円柱を描画
    circle = plt.Circle((0, 0), radius, fill=True, color='white', ec='black')
    plt.gca().add_patch(circle)
    
    # グラフ設定
    plt.title('円柱周りのポテンシャル流れ')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.axis('equal')
    plt.grid(True)
    plt.xlim(-5, 5)
    plt.ylim(-5, 5)
    
    # 画像を保存
    plt.savefig('cylinder_potential_flow.png', dpi=300, bbox_inches='tight')
    logger.info("ポテンシャル流れの可視化を 'cylinder_potential_flow.png' に保存しました")
    
    # プロットを表示
    plt.show()
    
    return True

def main():
    """メイン関数"""
    logger.info("ベクトル場の例を開始")
    
    # FreeFEMインターフェースを初期化
    ff = FreeFEMInterface(debug=True)
    
    # 例1: Sin波ベクトル場
    success = sine_wave_vector_field(ff)
    if not success:
        logger.error("Sin波ベクトル場の例が失敗しました")
    
    # 例2: 円柱周りのポテンシャル流れ
    success = potential_flow_around_cylinder(ff)
    if not success:
        logger.error("円柱周りのポテンシャル流れの例が失敗しました")
    
    logger.info("ベクトル場の例を終了")

if __name__ == "__main__":
    main() 