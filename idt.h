#include "../lib/types.h"
// JinoDB - встроенная KV база
#define MAX_KV 128
typedef struct { char key[32]; char value[128]; uint8_t used; } kv_t;
static kv_t db[MAX_KV];

void jdb_init(){ for(int i=0;i<MAX_KV;i++) db[i].used=0; }
int jdb_set(const char* k, const char* v){
    for(int i=0;i<MAX_KV;i++) if(db[i].used && strcmp(db[i].key,k)==0){
        int j=0; while(v[j]&&j<127){ db[i].value[j]=v[j]; j++; } db[i].value[j]=0; return 0;
    }
    for(int i=0;i<MAX_KV;i++) if(!db[i].used){
        int j=0; while(k[j]&&j<31){ db[i].key[j]=k[j]; j++; } db[i].key[j]=0;
        j=0; while(v[j]&&j<127){ db[i].value[j]=v[j]; j++; } db[i].value[j]=0;
        db[i].used=1; return 0;
    }
    return -1;
}
const char* jdb_get(const char* k){
    for(int i=0;i<MAX_KV;i++) if(db[i].used && strcmp(db[i].key,k)==0) return db[i].value;
    return 0;
}
