#include <iostream>
#include <cstring>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>
#include "ff++.hpp"
#include "AFunction.hpp"

// 浮動小数点配列の読み書きに関する操作を実装するFreeFEMプラグイン

using namespace Fem2D;
using namespace std;

// 共有メモリからdouble配列を読み取る関数
class ShmReadDoubleArray : public OneOperator {
public:
    // コンストラクタ
    ShmReadDoubleArray() : OneOperator(atype<KN<double>*>(), atype<string*>()) {}

    // 実行メソッド
    E_F0* code(const basicAC_F0& args) const {
        return new ShmReadDoubleArrayCode(args[0]->CastTo(args[0]->left()));
    }

    // コード実装クラス
    class ShmReadDoubleArrayCode : public E_F0 {
    private:
        Expression varname;
    public:
        ShmReadDoubleArrayCode(const E_F0* e) : varname(e) {}
        
        // evaluate関数の実装
        AnyType operator()(Stack stack) const {
            string* name = GetAny<string*>((*varname)(stack));
            KN<double>* result = new KN<double>();
            
            // 外部関数によって共有メモリから配列を読み取る
            // 共有メモリ読み取り処理をここに実装する予定
            // 以下は仮実装
            extern bool read_array_from_shared_memory(const char*, KN<double>*);
            if (!read_array_from_shared_memory(name->c_str(), result)) {
                cerr << "共有メモリからの配列読み取りに失敗: " << *name << endl;
            }
            
            Add2StackOfPtr2Free(stack, result);
            return SetAny<KN<double>*>(result);
        }
    };
};

// 共有メモリにdouble配列を書き込む関数
class ShmWriteDoubleArray : public OneOperator {
public:
    // コンストラクタ
    ShmWriteDoubleArray() : OneOperator(atype<long>(), atype<KN<double>*>(), atype<string*>()) {}

    // 実行メソッド
    E_F0* code(const basicAC_F0& args) const {
        return new ShmWriteDoubleArrayCode(args[0]->CastTo(args[0]->left()), 
                                        args[1]->CastTo(args[1]->left()));
    }

    // コード実装クラス
    class ShmWriteDoubleArrayCode : public E_F0 {
    private:
        Expression array_expr, varname;
    public:
        ShmWriteDoubleArrayCode(const E_F0* a, const E_F0* n) : array_expr(a), varname(n) {}
        
        // evaluate関数の実装
        AnyType operator()(Stack stack) const {
            KN<double>* array = GetAny<KN<double>*>((*array_expr)(stack));
            string* name = GetAny<string*>((*varname)(stack));
            
            // 外部関数によって共有メモリに配列を書き込む
            // 共有メモリ書き込み処理をここに実装する予定
            // 以下は仮実装
            extern bool write_array_to_shared_memory(const char*, const KN<double>*);
            if (!write_array_to_shared_memory(name->c_str(), array)) {
                cerr << "共有メモリへの配列書き込みに失敗: " << *name << endl;
                return SetAny<long>(0);
            }
            
            return SetAny<long>(1);
        }
    };
};

// 浮動小数点配列に対する演算を行う関数
class ScaleDoubleArray : public OneOperator {
public:
    // コンストラクタ
    ScaleDoubleArray() : OneOperator(atype<KN<double>*>(), atype<KN<double>*>(), atype<double>()) {}

    // 実行メソッド
    E_F0* code(const basicAC_F0& args) const {
        return new ScaleDoubleArrayCode(args[0]->CastTo(args[0]->left()), 
                                      args[1]->CastTo(args[1]->left()));
    }

    // コード実装クラス
    class ScaleDoubleArrayCode : public E_F0 {
    private:
        Expression array_expr, scale_expr;
    public:
        ScaleDoubleArrayCode(const E_F0* a, const E_F0* s) : array_expr(a), scale_expr(s) {}
        
        // evaluate関数の実装
        AnyType operator()(Stack stack) const {
            KN<double>* array = GetAny<KN<double>*>((*array_expr)(stack));
            double scale = GetAny<double>((*scale_expr)(stack));
            
            // 新しい配列を作成して結果を格納
            KN<double>* result = new KN<double>(array->N());
            
            // 配列の各要素にスケール係数を掛ける
            for (int i = 0; i < array->N(); i++) {
                (*result)[i] = (*array)[i] * scale;
            }
            
            Add2StackOfPtr2Free(stack, result);
            return SetAny<KN<double>*>(result);
        }
    };
};

// プラグインの初期化関数
static void init() {
    Global.Add("shmReadDoubleArray", "(", new ShmReadDoubleArray);
    Global.Add("shmWriteDoubleArray", "(", new ShmWriteDoubleArray);
    Global.Add("scaleDoubleArray", "(", new ScaleDoubleArray);
}

// FreeFEMプラグインの登録
LOADFUNC(init); 