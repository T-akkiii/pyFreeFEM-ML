#ifndef SHM_IMPLEMENTATION_HPP
#define SHM_IMPLEMENTATION_HPP

#include "ff++.hpp"

using namespace Fem2D;

// 外部から呼び出される関数のプロトタイプ宣言

/**
 * 共有メモリにdouble配列を書き込む
 * @param name 共有メモリの名前
 * @param array 書き込む配列
 * @return 成功した場合はtrue、失敗した場合はfalse
 */
bool write_array_to_shared_memory(const char* name, const KN<double>* array);

/**
 * 共有メモリからdouble配列を読み取る
 * @param name 共有メモリの名前
 * @param array 読み取った値を格納する配列
 * @return 成功した場合はtrue、失敗した場合はfalse
 */
bool read_array_from_shared_memory(const char* name, KN<double>* array);

// FreeFEMのプラグインで使用する関数宣言：配列書き込み
class ShmWriteDoubleArray : public OneOperator {
public:
    const int c_args[2] = {STRING_ARG, ARRAY_ARG};
    E_F0* code(const basicAC_F0& args) const;
    ShmWriteDoubleArray();
};

// FreeFEMのプラグインで使用する関数宣言：配列読み取り
class ShmReadDoubleArray : public OneOperator {
public:
    const int c_args[2] = {STRING_ARG, ARRAY_ARG};
    E_F0* code(const basicAC_F0& args) const;
    ShmReadDoubleArray();
};

// プラグインの初期化関数
static void init_shared_memory_operations();

#endif // SHM_IMPLEMENTATION_HPP 