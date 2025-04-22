# 共有メモリ通信ライブラリの使用例

このドキュメントでは、Python-FreeFEM間の共有メモリ通信ライブラリの使用例を紹介します。

## Python側の使用例

### 基本的な使用方法

```python
import numpy as np
from pyfreefem import FreeFEMInterface

# FreeFEMインターフェースの初期化
# Windows/WSL環境ではwsl_modeをTrueに設定
ff = FreeFEMInterface(wsl_mode=True, debug=True)

# NumPy配列データの準備
mesh_data = np.random.rand(100, 2)  # 100点のx,y座標
values = np.random.rand(100)  # 各点での値

# データを共有メモリに書き込み
ff.write_array(mesh_data, "mesh_points")
ff.write_array(values, "node_values")

# FreeFEMスクリプトの実行
script_path = "path/to/script.edp"
success, stdout, stderr = ff.run_script(script_path)

if success:
    # 計算結果の読み取り
    result = ff.read_array("result_values", 0, (100,), np.float64)
    print("計算結果:", result)
else:
    print("FreeFEM実行エラー:", stderr)

# リソースの解放
ff.cleanup()
```

### インラインスクリプトの実行

スクリプトファイルを作成せずに、直接Pythonコードから実行することも可能です：

```python
import numpy as np
from pyfreefem import FreeFEMInterface

ff = FreeFEMInterface(debug=True)

# サンプルデータを準備
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
ff.write_array(data, "input_data")

# インラインでFreeFEMスクリプトを実行
script = """
include "shm_comm.idp"

// 配列の宣言
real[int] values(5);

// 共有メモリからデータ読み込み
ReadRealArray(values, "input_data");

// 各値を2倍する
for (int i = 0; i < values.n; i++)
    values[i] = values[i] * 2;

// 結果を共有メモリに書き込み
WriteRealArray(values, "output_data");
"""

success, stdout, stderr = ff.run_inline_script(script)

if success:
    # 結果の読み取り (5要素のfloat64配列)
    result = ff.read_array("output_data", 0, (5,), np.float64)
    print("計算結果:", result)  # [2.0, 4.0, 6.0, 8.0, 10.0]を出力

ff.cleanup()
```

### スカラー値の読み書き

```python
from pyfreefem import FreeFEMInterface

ff = FreeFEMInterface()

# スカラー値の書き込み
ff.write_double(3.14159, "pi")
ff.write_int(42, "answer")
ff.write_string("Hello FreeFEM", "greeting")

# インラインスクリプト実行
script = """
include "shm_comm.idp"

// 共有メモリからスカラー値を読み込み
real pi_value;
int answer_value;
string greeting;

ReadDouble(pi_value, "pi");
ReadInt(answer_value, "answer");
ReadString(greeting, "greeting");

// 値を出力
cout << "Pi: " << pi_value << endl;
cout << "Answer: " << answer_value << endl;
cout << "Greeting: " << greeting << endl;

// 新しい値を書き込み
WriteDouble(2.71828, "e");
"""

ff.run_inline_script(script)

# 結果の読み取り
e_value = ff.read_double("e")
print(f"オイラー数: {e_value}")

ff.cleanup()
```

## FreeFEM側の使用例

### FreeFEMスクリプト例

```
// test_shm_comm.edp

// 共有メモリ通信ライブラリのインクルード
include "shm_comm.idp"

// SHM情報の表示
cout << "SHM name: " << GetShmName() << endl;
cout << "SHM size: " << GetShmSize() << endl;

// Python側から渡されたメッシュデータを読み込む
real[int, int] mesh_points(100, 2);
ReadRealMatrix(mesh_points, "mesh_points");

real[int] values(100);
ReadRealArray(values, "node_values");

// メッシュポイントと値を使った処理
// ... (メッシュ処理、解析等)

// 結果の準備
real[int] result(100);
for (int i = 0; i < result.n; i++) {
    // 何らかの計算（例: 値を2倍）
    result[i] = values[i] * 2.0;
}

// 結果をPython側に送信
WriteRealArray(result, "result_values");

cout << "処理完了" << endl;
```

### 共有メモリ通信ライブラリの直接呼び出し

デバッグや特別な用途の場合、FreeFEMスクリプトから直接共有メモリを操作できます：

```
// 共有メモリ通信ライブラリのインクルード
include "shm_comm.idp"

// 共有メモリ情報の表示
cout << "SHM名: " << GetShmName() << endl;
cout << "SHMサイズ: " << GetShmSize() << endl;

// 配列変数を宣言
real[int] array(5);
for (int i = 0; i < 5; i++) array[i] = i * 10;

// 配列を共有メモリに書き込み
WriteRealArray(array, "test_array");

// 共有メモリから配列を読み込み
real[int] read_array(5);
ReadRealArray(read_array, "test_array");

// 結果の表示
cout << "読み込まれた配列: ";
for (int i = 0; i < read_array.n; i++) {
    cout << read_array[i] << " ";
}
cout << endl;

// 整数配列のテスト
int[int] int_array(3);
for (int i = 0; i < 3; i++) int_array[i] = i + 1;

WriteIntArray(int_array, "int_test");

int[int] read_int_array(3);
ReadIntArray(read_int_array, "int_test");

cout << "読み込まれた整数配列: ";
for (int i = 0; i < read_int_array.n; i++) {
    cout << read_int_array[i] << " ";
}
cout << endl;
```

## サンプルアプリケーション: ポアソン方程式ソルバー

以下は、Python-FreeFEM間の共有メモリ通信を使用したポアソン方程式ソルバーの例です。

### Python側

```python
import numpy as np
import matplotlib.pyplot as plt
from pyfreefem import FreeFEMInterface

# FreeFEMインターフェースの初期化
ff = FreeFEMInterface(debug=True)

# 問題設定
domain_size = 1.0
mesh_size = 0.1
source_term = 1.0  # 右辺のソース項 f(x)

# パラメータを共有メモリに書き込み
ff.write_double(domain_size, "domain_size")
ff.write_double(mesh_size, "mesh_size")
ff.write_double(source_term, "source_term")

# ポアソン方程式を解くFreeFEMスクリプト
poisson_script = """
include "shm_comm.idp"

// パラメータの読み込み
real domain_size, mesh_size, source_term;
ReadDouble(domain_size, "domain_size");
ReadDouble(mesh_size, "mesh_size");
ReadDouble(source_term, "source_term");

// メッシュの作成
mesh Th = square(int(domain_size/mesh_size), int(domain_size/mesh_size));

// 有限要素空間
fespace Vh(Th, P1);
Vh u, v;

// 問題の定式化: -Δu = f
problem Poisson(u, v) = 
    int2d(Th)(
        dx(u)*dx(v) + dy(u)*dy(v)
    )
    - int2d(Th)(
        source_term*v
    )
    + on(1, 2, 3, 4, u=0);  // 境界条件

// 問題を解く
Poisson;

// 解のノード値を取得
real[int] solution(Vh.ndof);
for (int i = 0; i < Vh.ndof; i++) {
    solution[i] = u[][i];
}

// メッシュ情報を取得
real[int, int] mesh_points(Th.nv, 2);
for (int i = 0; i < Th.nv; i++) {
    mesh_points(i, 0) = Th(i).x;
    mesh_points(i, 1) = Th(i).y;
}

// 結果を共有メモリに書き込み
WriteRealMatrix(mesh_points, "mesh_points");
WriteRealArray(solution, "solution");
WriteInt(Th.nv, "num_vertices");
WriteInt(Th.nt, "num_triangles");

// 三角形要素の接続情報を書き込み
int[int, int] triangles(Th.nt, 3);
for (int i = 0; i < Th.nt; i++) {
    triangles(i, 0) = Th[i][0];
    triangles(i, 1) = Th[i][1];
    triangles(i, 2) = Th[i][2];
}
WriteIntMatrix(triangles, "triangles");
"""

# スクリプトを実行
success, stdout, stderr = ff.run_inline_script(poisson_script)

if success:
    # 結果の読み取り
    num_vertices = ff.read_int("num_vertices")
    num_triangles = ff.read_int("num_triangles")
    
    mesh_points = ff.read_array("mesh_points", 0, (num_vertices, 2), np.float64)
    solution = ff.read_array("solution", 0, (num_vertices,), np.float64)
    triangles = ff.read_array("triangles", 0, (num_triangles, 3), np.int32)
    
    print(f"頂点数: {num_vertices}")
    print(f"三角形要素数: {num_triangles}")
    
    # 結果の可視化
    plt.figure(figsize=(10, 8))
    plt.tripcolor(mesh_points[:, 0], mesh_points[:, 1], triangles, solution, 
                  shading='gouraud', cmap='viridis')
    plt.colorbar(label='Solution u(x,y)')
    plt.title('Poisson Equation Solution: -Δu = 1 with u=0 on boundary')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.axis('equal')
    plt.savefig('poisson_solution.png')
    plt.show()
else:
    print("FreeFEM実行エラー:", stderr)

# リソースの解放
ff.cleanup()
```

この例では、Pythonから問題パラメータをFreeFEMに渡し、FreeFEMでポアソン方程式を解いて、結果をPythonに戻しています。最後にMatplotlibを使用して解を可視化しています。 