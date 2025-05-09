#include "ff++.hpp"
#include "AFunction.hpp"
#include "InitFunct.hpp"
#include <iostream>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <string>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <map>
#include <vector>

#include "lgfem.hpp"

using namespace Fem2D;
using namespace std;

// 共有メモリセグメント情報の格納
struct SharedMemInfo {
    int id;           // 共有メモリID
    size_t size;      // サイズ
    void* addr;       // アタッチされたアドレス
    bool isAttached;  // アタッチ状態

    SharedMemInfo() : id(-1), size(0), addr(nullptr), isAttached(false) {}
    
    SharedMemInfo(int _id, size_t _size) 
        : id(_id), size(_size), addr(nullptr), isAttached(false) {}
};

// 共有メモリの管理クラス
class SharedMemoryManager {
private:
    static map<string, SharedMemInfo> segments;

public:
    // 共有メモリセグメントの作成
    static int Create(const string& name, size_t size) {
        key_t key = ftok(name.c_str(), 'R');
        if (key == -1) {
            cerr << "Error creating key: " << strerror(errno) << endl;
            return -1;
        }

        int shmid = shmget(key, size, IPC_CREAT | 0666);
        if (shmid == -1) {
            cerr << "Error creating shared memory: " << strerror(errno) << endl;
            return -1;
        }

        segments[name] = SharedMemInfo(shmid, size);
        return shmid;
    }

    // 共有メモリセグメントの破棄
    static bool Destroy(const string& name) {
        auto it = segments.find(name);
        if (it == segments.end()) {
            cerr << "Segment not found: " << name << endl;
            return false;
        }

        if (it->second.isAttached) {
            if (shmdt(it->second.addr) == -1) {
                cerr << "Error detaching memory: " << strerror(errno) << endl;
                return false;
            }
        }

        if (shmctl(it->second.id, IPC_RMID, nullptr) == -1) {
            cerr << "Error removing segment: " << strerror(errno) << endl;
            return false;
        }

        segments.erase(it);
        return true;
    }

    // 配列の書き込み
    static bool WriteArray(const string& name, const double* data, int size, int offset) {
        auto it = segments.find(name);
        if (it == segments.end()) {
            cerr << "Segment not found: " << name << endl;
            return false;
        }

        if (!it->second.isAttached) {
            it->second.addr = shmat(it->second.id, nullptr, 0);
            if (it->second.addr == (void*)-1) {
                cerr << "Error attaching memory: " << strerror(errno) << endl;
                return false;
            }
            it->second.isAttached = true;
        }

        if (offset + size * sizeof(double) > it->second.size) {
            cerr << "Array too large for segment" << endl;
            return false;
        }

        memcpy((char*)it->second.addr + offset, data, size * sizeof(double));
        return true;
    }

    // 配列の読み込み
    static bool ReadArray(const string& name, double* data, int size, int offset) {
        auto it = segments.find(name);
        if (it == segments.end()) {
            cerr << "Segment not found: " << name << endl;
            return false;
        }

        if (!it->second.isAttached) {
            it->second.addr = shmat(it->second.id, nullptr, 0);
            if (it->second.addr == (void*)-1) {
                cerr << "Error attaching memory: " << strerror(errno) << endl;
                return false;
            }
            it->second.isAttached = true;
        }

        if (offset + size * sizeof(double) > it->second.size) {
            cerr << "Array too large for segment" << endl;
            return false;
        }

        memcpy(data, (char*)it->second.addr + offset, size * sizeof(double));
        return true;
    }
};

map<string, SharedMemInfo> SharedMemoryManager::segments;

// FreeFEM++インターフェース関数
class ShmCreate : public OneOperator {
public:
    ShmCreate() : OneOperator(atype<double>(), atype<string>(), atype<double>()) {}

    E_F0* code(const basicAC_F0& args) const {
        return new ShmCreateCode(args[0], args[1]);
    }

    class ShmCreateCode : public E_F0 {
        Expression name;
        Expression size;
    public:
        ShmCreateCode(Expression n, Expression s) : name(n), size(s) {}

        AnyType operator()(Stack stack) const {
            string sname = GetAny<string>((*name)(stack));
            int ssize = GetAny<double>((*size)(stack));
            return SetAny<double>(SharedMemoryManager::Create(sname, ssize));
        }
    };
};

class ShmDestroy : public OneOperator {
public:
    ShmDestroy() : OneOperator(atype<double>(), atype<string>()) {}

    E_F0* code(const basicAC_F0& args) const {
        return new ShmDestroyCode(args[0]);
    }

    class ShmDestroyCode : public E_F0 {
        Expression name;
    public:
        ShmDestroyCode(Expression n) : name(n) {}

        AnyType operator()(Stack stack) const {
            string sname = GetAny<string>((*name)(stack));
            return SetAny<double>(SharedMemoryManager::Destroy(sname) ? 1.0 : 0.0);
        }
    };
};

class ArrayInfo {
public:
    int size;
    int offset;

    ArrayInfo(int s = 0, int o = 0) : size(s), offset(o) {}
};

class ShmWriteArray : public OneOperator {
public:
    ShmWriteArray() : OneOperator(atype<double>(), atype<string>(), atype<KN<double>*>(), atype<ArrayInfo>()) {}

    E_F0* code(const basicAC_F0& args) const {
        return new ShmWriteArrayCode(args[0], args[1], args[2]);
    }

    class ShmWriteArrayCode : public E_F0 {
        Expression name;
        Expression array;
        Expression info;
    public:
        ShmWriteArrayCode(Expression n, Expression a, Expression i) : name(n), array(a), info(i) {}

        AnyType operator()(Stack stack) const {
            string sname = GetAny<string>((*name)(stack));
            KN<double>* data = GetAny<KN<double>*>((*array)(stack));
            ArrayInfo ainfo = GetAny<ArrayInfo>((*info)(stack));

            return SetAny<double>(SharedMemoryManager::WriteArray(sname, data->operator double*(), ainfo.size, ainfo.offset) ? 1.0 : 0.0);
        }
    };
};

class ShmReadArray : public OneOperator {
public:
    ShmReadArray() : OneOperator(atype<double>(), atype<string>(), atype<KN<double>*>(), atype<ArrayInfo>()) {}

    E_F0* code(const basicAC_F0& args) const {
        return new ShmReadArrayCode(args[0], args[1], args[2]);
    }

    class ShmReadArrayCode : public E_F0 {
        Expression name;
        Expression array;
        Expression info;
    public:
        ShmReadArrayCode(Expression n, Expression a, Expression i) : name(n), array(a), info(i) {}

        AnyType operator()(Stack stack) const {
            string sname = GetAny<string>((*name)(stack));
            KN<double>* data = GetAny<KN<double>*>((*array)(stack));
            ArrayInfo ainfo = GetAny<ArrayInfo>((*info)(stack));

            return SetAny<double>(SharedMemoryManager::ReadArray(sname, data->operator double*(), ainfo.size, ainfo.offset) ? 1.0 : 0.0);
        }
    };
};

static void init() {
    cout << "Loading mmap-semaphore plugin..." << endl;
    Global.Add("ShmCreate", "(", new ShmCreate);
    Global.Add("ShmDestroy", "(", new ShmDestroy);
    Global.Add("ShmWriteArray", "(", new ShmWriteArray);
    Global.Add("ShmReadArray", "(", new ShmReadArray);
    cout << "Plugin loaded successfully" << endl;
}

LOADFUNC(init) 