#include "shm_implementation.hpp"

#include <iostream>
#include <cstring>
#include <string>
#include <vector>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <semaphore.h>
#include <errno.h>

// FreeFEMプラグイン用の共有メモリ実装

using namespace Fem2D;
using namespace std;

// 共有メモリ構造体
struct SharedMemoryData {
    size_t size;           // データのサイズ（バイト単位）
    size_t elements;       // 要素数（配列の場合）
    char data_type[32];    // データ型の文字列表現（"int", "double", "double_array"など）
    char semaphore_name[64]; // セマフォ名
};

// 共有メモリオブジェクトを管理するクラス
class SharedMemoryManager {
private:
    static const int MAX_SHM_OBJECTS = 100;
    static struct {
        string name;
        void* addr;
        size_t size;
        int fd;
        bool in_use;
    } shm_objects[MAX_SHM_OBJECTS];

    // 空きスロットを検索
    static int find_free_slot() {
        for (int i = 0; i < MAX_SHM_OBJECTS; i++) {
            if (!shm_objects[i].in_use) {
                return i;
            }
        }
        return -1;
    }

    // 名前からスロットを検索
    static int find_slot_by_name(const string& name) {
        for (int i = 0; i < MAX_SHM_OBJECTS; i++) {
            if (shm_objects[i].in_use && shm_objects[i].name == name) {
                return i;
            }
        }
        return -1;
    }

public:
    // 共有メモリオブジェクトを作成または開く
    static int create_or_open(const string& name, size_t size) {
        int slot = find_slot_by_name(name);
        if (slot >= 0) {
            // 既に存在する場合は再利用
            return slot;
        }

        slot = find_free_slot();
        if (slot < 0) {
            cerr << "共有メモリオブジェクトの最大数に達しました" << endl;
            return -1;
        }

        // 共有メモリオブジェクトを開く
        int fd = shm_open(name.c_str(), O_CREAT | O_RDWR, 0666);
        if (fd < 0) {
            cerr << "共有メモリのオープンに失敗: " << name << ", エラー: " << strerror(errno) << endl;
            return -1;
        }

        // サイズを設定
        if (ftruncate(fd, size) < 0) {
            cerr << "共有メモリのサイズ設定に失敗: " << name << ", エラー: " << strerror(errno) << endl;
            close(fd);
            return -1;
        }

        // メモリマッピング
        void* addr = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (addr == MAP_FAILED) {
            cerr << "メモリマッピングに失敗: " << name << ", エラー: " << strerror(errno) << endl;
            close(fd);
            return -1;
        }

        // スロットに情報を格納
        shm_objects[slot].name = name;
        shm_objects[slot].addr = addr;
        shm_objects[slot].size = size;
        shm_objects[slot].fd = fd;
        shm_objects[slot].in_use = true;

        return slot;
    }

    // 共有メモリオブジェクトを閉じる
    static void close(int slot) {
        if (slot < 0 || slot >= MAX_SHM_OBJECTS || !shm_objects[slot].in_use) {
            return;
        }

        munmap(shm_objects[slot].addr, shm_objects[slot].size);
        ::close(shm_objects[slot].fd);
        shm_objects[slot].in_use = false;
    }

    // 共有メモリオブジェクトを削除
    static void unlink(const string& name) {
        shm_unlink(name.c_str());
    }

    // スロットからアドレスを取得
    static void* get_address(int slot) {
        if (slot < 0 || slot >= MAX_SHM_OBJECTS || !shm_objects[slot].in_use) {
            return NULL;
        }
        return shm_objects[slot].addr;
    }

    // 名前からアドレスを取得
    static void* get_address(const string& name) {
        int slot = find_slot_by_name(name);
        if (slot < 0) {
            return NULL;
        }
        return shm_objects[slot].addr;
    }
};

// 静的メンバの初期化
decltype(SharedMemoryManager::shm_objects) SharedMemoryManager::shm_objects = {};

// 外部から呼び出される関数：共有メモリに配列を書き込む
bool write_array_to_shared_memory(const char* name, const KN<double>* array) {
    if (!array) {
        cerr << "無効な配列ポインタです" << endl;
        return false;
    }

    size_t elements = array->N();
    size_t data_size = elements * sizeof(double);
    size_t total_size = sizeof(SharedMemoryData) + data_size;
    
    // 共有メモリを作成または開く
    string shm_name = string("/") + name;
    int slot = SharedMemoryManager::create_or_open(shm_name, total_size);
    if (slot < 0) {
        return false;
    }
    
    // 共有メモリ構造体にデータを書き込む
    SharedMemoryData* shm_data = static_cast<SharedMemoryData*>(SharedMemoryManager::get_address(slot));
    shm_data->size = data_size;
    shm_data->elements = elements;
    strcpy(shm_data->data_type, "double_array");
    
    // セマフォ名を設定
    string sem_name = string("/sem_") + name;
    strcpy(shm_data->semaphore_name, sem_name.c_str());
    
    // セマフォを作成または開く
    sem_t* semaphore = sem_open(sem_name.c_str(), O_CREAT, 0666, 0);
    if (semaphore == SEM_FAILED) {
        cerr << "セマフォのオープンに失敗: " << sem_name << ", エラー: " << strerror(errno) << endl;
        return false;
    }
    
    // データ部分にdouble配列をコピー
    double* data_ptr = reinterpret_cast<double*>(static_cast<char*>(SharedMemoryManager::get_address(slot)) + sizeof(SharedMemoryData));
    for (size_t i = 0; i < elements; i++) {
        data_ptr[i] = (*array)[i];
    }
    
    // セマフォを解放して、データが利用可能であることを示す
    sem_post(semaphore);
    sem_close(semaphore);
    
    return true;
}

// 外部から呼び出される関数：共有メモリから配列を読み取る
bool read_array_from_shared_memory(const char* name, KN<double>* array) {
    if (!array) {
        cerr << "無効な配列ポインタです" << endl;
        return false;
    }
    
    // 共有メモリを開く
    string shm_name = string("/") + name;
    
    // 最初に小さなサイズで開き、実際のサイズを確認する
    int slot = SharedMemoryManager::create_or_open(shm_name, sizeof(SharedMemoryData));
    if (slot < 0) {
        return false;
    }
    
    // 共有メモリ構造体からデータサイズを読み取る
    SharedMemoryData* shm_data = static_cast<SharedMemoryData*>(SharedMemoryManager::get_address(slot));
    
    // セマフォを開く
    sem_t* semaphore = sem_open(shm_data->semaphore_name, 0);
    if (semaphore == SEM_FAILED) {
        cerr << "セマフォのオープンに失敗: " << shm_data->semaphore_name << ", エラー: " << strerror(errno) << endl;
        return false;
    }
    
    // セマフォを待機（データが利用可能になるまで）
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    ts.tv_sec += 10; // 10秒のタイムアウト
    if (sem_timedwait(semaphore, &ts) < 0) {
        cerr << "セマフォ待機中にタイムアウトまたはエラー: " << strerror(errno) << endl;
        sem_close(semaphore);
        return false;
    }
    
    // データ型の確認
    if (strcmp(shm_data->data_type, "double_array") != 0) {
        cerr << "データ型が一致しません: " << shm_data->data_type << " (期待値: double_array)" << endl;
        sem_post(semaphore); // セマフォを戻す
        sem_close(semaphore);
        return false;
    }
    
    // 配列サイズの設定
    size_t elements = shm_data->elements;
    array->resize(elements);
    
    // データをコピー
    double* data_ptr = reinterpret_cast<double*>(static_cast<char*>(SharedMemoryManager::get_address(slot)) + sizeof(SharedMemoryData));
    for (size_t i = 0; i < elements; i++) {
        (*array)[i] = data_ptr[i];
    }
    
    // セマフォを解放して、データが読み取られたことを示す
    sem_post(semaphore);
    sem_close(semaphore);
    
    return true;
}

// FreeFEMのプラグイン関数：共有メモリへの書き込み実装
class WriteArrayCode : public E_F0mps {
public:
    Expression shm_name;
    Expression array_expr;
    
    WriteArrayCode(const basicAC_F0& args) : shm_name(args[0]), array_expr(args[1]) {}
    
    AnyType operator()(Stack stack) const {
        string* name = GetAny<string*>((*shm_name)(stack));
        KN<double>* array = GetAny<KN<double>*>((*array_expr)(stack));
        
        bool success = write_array_to_shared_memory(name->c_str(), array);
        return success ? 1L : 0L;
    }
};

E_F0* ShmWriteDoubleArray::code(const basicAC_F0& args) const {
    return new WriteArrayCode(args);
}

ShmWriteDoubleArray::ShmWriteDoubleArray() : OneOperator(atype<long>(), atype<string*>(), atype<KN<double>*>()) {}

// FreeFEMのプラグイン関数：共有メモリからの読み取り実装
class ReadArrayCode : public E_F0mps {
public:
    Expression shm_name;
    Expression array_expr;
    
    ReadArrayCode(const basicAC_F0& args) : shm_name(args[0]), array_expr(args[1]) {}
    
    AnyType operator()(Stack stack) const {
        string* name = GetAny<string*>((*shm_name)(stack));
        KN<double>* array = GetAny<KN<double>*>((*array_expr)(stack));
        
        bool success = read_array_from_shared_memory(name->c_str(), array);
        return success ? 1L : 0L;
    }
};

E_F0* ShmReadDoubleArray::code(const basicAC_F0& args) const {
    return new ReadArrayCode(args);
}

ShmReadDoubleArray::ShmReadDoubleArray() : OneOperator(atype<long>(), atype<string*>(), atype<KN<double>*>()) {}

// プラグインの初期化関数
static void init_shared_memory_operations() {
    Global.Add("writeSharedMemory", "(", new ShmWriteDoubleArray);
    Global.Add("readSharedMemory", "(", new ShmReadDoubleArray);
}

// FreeFEMプラグインのエントリポイント
LOADFUNC(init_shared_memory_operations) 