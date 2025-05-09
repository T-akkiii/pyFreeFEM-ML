from pyfreefem_ml import PyFreeFEM
import numpy as np
import os
import tempfile

# 2次元テストデータ作成
test_array = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
print(f"入力配列: 形状={test_array.shape}, データ={test_array}")

# 統一インターフェースを使用して初期化
ff = PyFreeFEM(
    wsl_mode=True,  # WSL環境を使用
    debug=True
)

# 多次元配列のテストスクリプトを作成 - ASCII文字のみを使用
edp_script = """
// Multi-dimensional array test FreeFEM script
// Input: Flattened 2x3 matrix
// Output: Input array elements multiplied by 2

// Matrix size definition
int ny = 2;
int nx = 3;
int npoints = ny*nx;

// Read input data
real[int] inputArray(npoints);
{
    ifstream inputFile("input.txt");
    for(int i = 0; i < npoints; i++)
        inputFile >> inputArray[i];
}

// Create output array and compute
real[int] outputArray(npoints);
for(int i = 0; i < npoints; i++)
    outputArray[i] = inputArray[i] * 2.0;

// Output metadata file (matrix shape information)
{
    ofstream metaFile("matrix_metadata.txt");
    metaFile << 1 << " " << npoints << endl;  // One function, number of data points
    metaFile << nx << " " << ny << endl;      // Matrix size
}

// Save output data
{
    ofstream outputFile("output.txt");
    for(int i = 0; i < npoints; i++)
        outputFile << outputArray[i] << " ";
}
"""

# 一時ディレクトリを作成
tmp_dir = tempfile.mkdtemp()
script_path = os.path.join(tmp_dir, "multi_array_test.edp")
with open(script_path, "w", encoding="utf-8") as f:
    f.write(edp_script)
print(f"スクリプトを作成しました: {script_path}")

# テスト実行
success, result, stdout, stderr = ff.run_script(
    script_path,
    input_data=test_array.flatten(),
    metadata_file='matrix_metadata.txt'
)

if success:
    print(f"出力配列: 形状={result.shape}, データ={result}")
else:
    print(f"エラー: {stderr}")