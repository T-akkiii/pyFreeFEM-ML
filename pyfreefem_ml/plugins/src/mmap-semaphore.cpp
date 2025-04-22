// FreeFEM++ plugin for shared memory operations
#include <iostream>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <string>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <map>
#include <vector>

#include "AFunction.hpp"
#include "InitFunct.hpp" // LOADFUNCマクロのために必要

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
    // 名前と共有メモリ情報のマッピング
    static map<string, SharedMemInfo> sharedMemories;
    
    // 一意のキーを生成
    static key_t generateKey(const string& name) {
        // シンプルなハッシュ関数
        key_t key = 0;
        for (char c : name) {
            key = (key * 31 + c) & 0x7FFFFFFF; // 正の値を保証
        }
        // プロセスIDを混ぜて一意性を高める
        key = (key ^ (getpid() << 16)) & 0x7FFFFFFF;
        return key;
    }

public:
    // 共有メモリの作成
    static int create(const string& name, size_t size) {
        // 既に同名の共有メモリが存在する場合はエラー
        if (sharedMemories.find(name) != sharedMemories.end()) {
            cerr << "Shared memory with name '" << name << "' already exists" << endl;
            return -1;
        }
        
        // キーの生成
        key_t key = generateKey(name);
        cout << "Generated key: " << key << " for name: " << name << endl;
        
        // 共有メモリセグメントの作成
        int shmid = shmget(key, size, IPC_CREAT | 0666);
        if (shmid == -1) {
            cerr << "Error creating shared memory: " << strerror(errno) << endl;
            return -1;
        }
        
        // 情報の保存
        sharedMemories[name] = SharedMemInfo(shmid, size);
        cout << "Created shared memory with id: " << shmid << " and size: " << size << endl;
        
        return shmid;
    }
    
    // 共有メモリの破棄
    static bool destroy(const string& name) {
        auto it = sharedMemories.find(name);
        if (it == sharedMemories.end()) {
            cerr << "Shared memory with name '" << name << "' does not exist" << endl;
            return false;
        }
        
        // アタッチされている場合はデタッチ
        if (it->second.isAttached && it->second.addr != nullptr) {
            if (shmdt(it->second.addr) == -1) {
                cerr << "Error detaching shared memory: " << strerror(errno) << endl;
                return false;
            }
        }
        
        // 共有メモリの削除
        if (shmctl(it->second.id, IPC_RMID, NULL) == -1) {
            cerr << "Error destroying shared memory: " << strerror(errno) << endl;
            return false;
        }
        
        // マップから削除
        sharedMemories.erase(it);
        cout << "Successfully destroyed shared memory '" << name << "'" << endl;
        
        return true;
    }
    
    // 共有メモリへの書き込み
    static bool write(const string& name, const void* data, size_t size, size_t offset = 0) {
        auto it = sharedMemories.find(name);
        if (it == sharedMemories.end()) {
            cerr << "Shared memory with name '" << name << "' does not exist" << endl;
            return false;
        }
        
        // サイズチェック
        if (offset + size > it->second.size) {
            cerr << "Write operation exceeds shared memory size" << endl;
            return false;
        }
        
        // アタッチされていない場合は自動的にアタッチ
        if (!it->second.isAttached || it->second.addr == nullptr) {
            it->second.addr = shmat(it->second.id, NULL, 0);
            if (it->second.addr == (void*)-1) {
                cerr << "Error attaching shared memory: " << strerror(errno) << endl;
                it->second.addr = nullptr;
                return false;
            }
            it->second.isAttached = true;
        }
        
        // データコピー
        memcpy((char*)it->second.addr + offset, data, size);
        cout << "Successfully wrote " << size << " bytes to shared memory '" << name << "'" << endl;
        
        return true;
    }
    
    // 共有メモリからの読み込み
    static bool read(const string& name, void* data, size_t size, size_t offset = 0) {
        auto it = sharedMemories.find(name);
        if (it == sharedMemories.end()) {
            cerr << "Shared memory with name '" << name << "' does not exist" << endl;
            return false;
        }
        
        // サイズチェック
        if (offset + size > it->second.size) {
            cerr << "Read operation exceeds shared memory size" << endl;
            return false;
        }
        
        // アタッチされていない場合は自動的にアタッチ
        if (!it->second.isAttached || it->second.addr == nullptr) {
            it->second.addr = shmat(it->second.id, NULL, 0);
            if (it->second.addr == (void*)-1) {
                cerr << "Error attaching shared memory: " << strerror(errno) << endl;
                it->second.addr = nullptr;
                return false;
            }
            it->second.isAttached = true;
        }
        
        // データコピー
        memcpy(data, (char*)it->second.addr + offset, size);
        cout << "Successfully read " << size << " bytes from shared memory '" << name << "'" << endl;
        
        return true;
    }
    
    // 登録されている共有メモリの一覧を取得
    static vector<string> list() {
        vector<string> names;
        for (const auto& pair : sharedMemories) {
            names.push_back(pair.first);
        }
        return names;
    }
    
    // クリーンアップ処理（すべての共有メモリを破棄）
    static void cleanup() {
        vector<string> names;
        for (const auto& pair : sharedMemories) {
            names.push_back(pair.first);
        }
        
        for (const auto& name : names) {
            destroy(name);
        }
        
        sharedMemories.clear();
    }
};

// 静的メンバの初期化
map<string, SharedMemInfo> SharedMemoryManager::sharedMemories;

// 4引数の関数を3引数で扱うための構造体
class ArrayInfo {
public:
    double size;    // 配列のサイズ
    double offset;  // オフセット
    
    ArrayInfo() : size(0), offset(0) {}
    ArrayInfo(double s, double o) : size(s), offset(o) {}
};

extern "C" {

// FreeFEM++ wrapper functions

// 共有メモリ作成
double shm_create(string* const& name, const double& size) {
    int shmid = SharedMemoryManager::create(*name, static_cast<size_t>(size));
    return static_cast<double>(shmid);
}

// 共有メモリ破棄
double shm_destroy(string* const& name) {
    bool result = SharedMemoryManager::destroy(*name);
    return result ? 1.0 : 0.0;
}

// double配列の書き込み - 3引数バージョン
double shm_write_array(string* const& name, double* const& data, ArrayInfo* const& info) {
    size_t size = static_cast<size_t>(info->size) * sizeof(double);
    bool result = SharedMemoryManager::write(*name, data, size, static_cast<size_t>(info->offset));
    return result ? 1.0 : 0.0;
}

// double配列の読み込み - 3引数バージョン
double shm_read_array(string* const& name, double* const& data, ArrayInfo* const& info) {
    size_t size = static_cast<size_t>(info->size) * sizeof(double);
    bool result = SharedMemoryManager::read(*name, data, size, static_cast<size_t>(info->offset));
    return result ? 1.0 : 0.0;
}

// ArrayInfo構造体を作成する関数
ArrayInfo* create_array_info(const double& size, const double& offset) {
    return new ArrayInfo(size, offset);
}

// プラグイン登録
class Init {
public:
    Init() {
        cout << "Registering shared memory functions..." << endl;
        
        // 共有メモリの作成・破棄
        Global.Add("ShmCreate", "(", new OneOperator2_<double, string*, double>(shm_create));
        Global.Add("ShmDestroy", "(", new OneOperator1_<double, string*>(shm_destroy));
        
        // ArrayInfo構造体の作成
        Global.Add("ArrayInfo", "(", new OneOperator2_<ArrayInfo*, double, double>(create_array_info));
        
        // 配列の読み書き (3引数バージョン)
        // FreeFEM 4.10では、OneOperator3_は<R,A,B,C>の形式で使用する
        Global.Add("ShmWriteArray", "(", new OneOperator3_<double, string*, double*, ArrayInfo*>(shm_write_array));
        Global.Add("ShmReadArray", "(", new OneOperator3_<double, string*, double*, ArrayInfo*>(shm_read_array));
    }
    
    ~Init() {
        // プラグインのアンロード時に自動的にクリーンアップ
        SharedMemoryManager::cleanup();
    }
};

static Init init;

// FreeFEM++からの初期化関数
void Load_Init() {
    cout << "Loading mmap-semaphore plugin..." << endl;
    cout << "Plugin loaded successfully" << endl;
}

LOADFUNC(Load_Init)

} // end of extern "C" 