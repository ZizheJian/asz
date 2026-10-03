#pragma once

#include <cassert>
#include <map>
#include <queue>
#include <stack>
#include <vector>
#include <unordered_map>
#include <cstdio>
#include <cstdlib>
#include <cstdint>

using namespace std;

template <class T>
class huffman_encoder_class
{
    private:
        class Node 
        {
            public:
                uint64_t c;
                Node *p[2];

                Node(uint64_t c_=0,Node *lp=nullptr,Node *rp=nullptr)
                {
                    c=c_;
                    p[0]=lp;
                    p[1]=rp;
                }

                inline unsigned char isLeaf()
                { 
                    return p[0]==nullptr;
                }
        };

        class HuffmanTree 
        {
            private:
                unsigned char _constructed=0;

                unsigned char len=0;
                int vec=0;

                class cmp
                {
                    public:
                        bool operator()(const pair<uint64_t,uint64_t> &u,const pair<uint64_t,uint64_t> &v) 
                        {
                            return u.second==v.second?u.first>v.first:u.second>v.second;
                        }
                };

            public:
                void dfs_mp(Node *u)
                {
                    if (u->isLeaf())
                    {
                        mplen[u->c]=len;
                        mpcode[u->c]=vec;
                        limit=std::max(limit,len);
                        return;
                    }
                    ++len;
                    dfs_mp(u->p[0]);
                    --len;
                    vec^=1<<len++;
                    dfs_mp(u->p[1]);
                    vec^=1<<--len;
                }

                void dfs_vec(Node *u)
                {
                    if (u->isLeaf())
                    {
                        veclen[u->c]=len;
                        veccode[u->c]=vec;
                        limit=std::max(limit,len);
                        return;
                    }
                    ++len;
                    dfs_vec(u->p[0]);
                    --len;
                    vec^=1<<len++;
                    dfs_vec(u->p[1]);
                    vec^=1<<--len;
                }

                unsigned char usemp;
                // 0 : vec
                // 1 : mp

                std::vector<unsigned char> veclen;
                std::vector<int> veccode;
                unordered_map<uint64_t,unsigned char> mplen;
                unordered_map<uint64_t,int> mpcode;

                T offset;
                // minimum bits for T
                unsigned char mbft;
                unsigned char limit;

                void init()
                {
                    _constructed=0;
                    ht.clear();
                    veclen.clear();
                    veccode.clear();
                    mplen.clear();
                    mpcode.clear();
                    vecfreq.clear();
                    mpfreq.clear();
                    decode_table.clear();

                    offset=0;
                    mbft=0;
                    root=0;
                    n=0;
                    maxval=0;
                    limit=0;
                    decode_table_bits=0;
                }

                HuffmanTree()
                {
                    init();
                }

                uint64_t root;
                uint64_t n;//node数量
                T maxval;
                std::vector<Node> ht;
                std::vector<uint64_t> vecfreq;//以vector形式存储的freq
                unordered_map<uint64_t,uint64_t> mpfreq;//以map形式存储的freq

                struct DecodeEntry
                {
                    Node *node=nullptr;
                    T symbol=0;
                    unsigned char len=0;
                };
                std::vector<DecodeEntry> decode_table;
                unsigned char decode_table_bits=0;
                static constexpr uint64_t decode_table_symbol_limit=1024;
                static constexpr unsigned char decode_table_bit_limit=12;

                void buildDecodeTable()
                {
                    // Small alphabets benefit from a prefix table; large ones retain the cache-friendlier tree walk.
                    if (n>decode_table_symbol_limit)
                        return;
                    decode_table_bits=std::min<unsigned char>(limit,decode_table_bit_limit);
                    decode_table.resize(1ull<<decode_table_bits);
                    for (uint64_t prefix=0;prefix<decode_table.size();prefix++)
                    {
                        Node *u=&ht[root];
                        unsigned char len=0;
                        while (len<decode_table_bits&&!u->isLeaf())
                            u=u->p[(prefix>>len++)&1];
                        DecodeEntry &entry=decode_table[prefix];
                        if (u->isLeaf())
                        {
                            entry.symbol=(T)(u->c+offset);
                            entry.len=len;
                        }
                        else
                            entry.node=u;
                    }
                }

                void addElementInMap(uint64_t c,uint64_t freqc)
                {
                    assert(!_constructed);
                    ht.push_back(Node(c));
                    mpfreq[c]=freqc;
                    ++n;
                }

                void addElementInVector(uint64_t c,uint64_t freqc)
                {
                    assert(!_constructed);
                    ht.push_back(Node(c));
                    vecfreq[c]=freqc;
                    ++n;
                }

                void constructHuffmanTree()
                {
                    assert(!_constructed);

                    if (n==1 || maxval==1)
                    {
                        mbft=1;
                        maxval=1;
                        offset+=ht[0].c;
                        ht[0].c=0;
                        ht.push_back(Node(0,&ht[0],nullptr));
                        if (usemp) 
                        {
                            mplen[0]=1;
                            mpcode[0]=0;
                        }
                        else
                        {
                            veclen[0]=1;
                            veccode[0]=0;
                        }
                        limit=1;
                        setConstructed();
                        return;
                    }

                    mbft=1;
                    while ((1llu<<mbft)<static_cast<uint64_t>(maxval))
                        ++mbft;

                    priority_queue<pair<uint64_t,uint64_t>,vector<pair<uint64_t,uint64_t>>,cmp> q;

                    if (usemp)
                        for (uint64_t i=0;i<ht.size();i++)
                            q.push({i,mpfreq[ht[i].c]});
                    else
                        for (uint64_t i=0;i<ht.size();i++)
                            q.push({i,vecfreq[ht[i].c]});

                    while (q.size()>1)
                    {
                        uint64_t u=q.top().first;
                        uint64_t freq_u=q.top().second;
                        q.pop();
                        uint64_t v=q.top().first;
                        uint64_t freq_v=q.top().second;
                        q.pop();
                        ht.push_back(Node(0,&ht[u],&ht[v]));
                        q.push({ht.size()-1,freq_u+freq_v});
                    }

                    root=ht.size()-1;

                    if (usemp)
                        dfs_mp(&ht[root]);
                    else
                        dfs_vec(&ht[root]);

                    setConstructed();

                }

                unsigned char isConstructed() 
                {
                    return _constructed;
                }

                void setConstructed()
                {
                    _constructed=1;
                }
        };

        HuffmanTree tree;

    public:
        void preprocess_encode(const T* const bins,uint64_t num_bin)
        {
            tree.init();
            T __minval,__maxval;
            __minval=*bins;
            __maxval=*bins;
            for (uint64_t i=1;i<num_bin;i++)
            {
                __minval=min(__minval,*(bins+i));
                __maxval=max(__maxval,*(bins+i));
            }
            tree.offset=__minval;
            tree.maxval=__maxval-__minval+1;
            // bin的值密集时使用vector存储频次，稀疏时使用map存储频次
            if ((tree.maxval>=(1<<12) and num_bin<2*static_cast<uint64_t>(__maxval)) || tree.maxval>=(1<<28))
                tree.usemp=1;
            else
                tree.usemp=0;
            if (tree.usemp)
            {
                map<uint64_t,uint64_t> freq;
                for (uint64_t i=0;i<num_bin;i++)
                    ++freq[static_cast<uint64_t>(bins[i]-tree.offset)];
                tree.ht.reserve(freq.size()<<1);
                for (auto it:freq)
                    tree.addElementInMap(it.first,it.second);
            }
            else
            {
                tree.vecfreq.resize(tree.maxval);
                tree.veclen.resize(tree.maxval);
                tree.veccode.resize(tree.maxval);
                std::vector<uint64_t> freq(tree.maxval);
                for (uint64_t i=0;i<num_bin;i++)
                    ++freq[static_cast<uint64_t>(bins[i]-tree.offset)];
                tree.ht.reserve(freq.size()<<1);
                for (uint64_t i=0;i<static_cast<uint64_t>(tree.maxval);i++)
                    if (freq[i]) 
                        tree.addElementInVector(i,freq[i]);
            }
            tree.constructHuffmanTree();
        }

        uint64_t encode(const T *bins,uint64_t num_bin,unsigned char*& bytes)
        {
            if (tree.maxval==1)
            {
                int64ToBytes_bigEndian(bytes,num_bin^0x1234abcd);
                bytes+=8;
                return 8;
            }

            assert(tree.isConstructed());
            unsigned char* head=bytes;
            bytes+=8;

            uint64_t len=0;

            unsigned char mask=0;
            unsigned char index=0;

            if (tree.usemp)
                for (uint64_t i=0;i<num_bin;i++)
                {
                    const T& it=bins[i];
                    const unsigned char& len_i=tree.mplen[it-tree.offset];
                    const int& code_i=tree.mpcode[it-tree.offset];
                    len+=len_i;
                    writeBytes(bytes,code_i,len_i,mask,index);
                }
            else
                for (uint64_t i=0;i<num_bin;i++) 
                {
                    const T& it=bins[i];
                    const unsigned char& len_i=tree.veclen[it-tree.offset];
                    const int& code_i=tree.veccode[it-tree.offset];
                    len+=len_i;
                    writeBytes(bytes,code_i,len_i,mask,index);
                }
            
            writeBytesClearMask(bytes,mask,index);

            int64ToBytes_bigEndian(head,len^0x1234abcd);

            return bytes-head;
        }

        void decode(const unsigned char*& bytes,T *out,uint64_t targetLength)
        {
            if (tree.maxval==1)
            {
                uint64_t count=bytesToInt64_bigEndian(bytes)^0x1234abcd;
                bytes+=8;
                if (targetLength&&count!=targetLength)
                    throw runtime_error("Huffman payload length does not match its value count");
                for (uint64_t i=0;i<count;i++)
                    out[i]=tree.offset;
                return;
            }

            assert(tree.isConstructed());

            uint64_t len=bytesToInt64_bigEndian(bytes)^0x1234abcd;
            bytes+=8;
            if (tree.decode_table.empty())
            {
                uint64_t outLen=0,byte_index=0,bit_pos=0;
                Node *u=&tree.ht[tree.root];
                for (;bit_pos+8<len;bit_pos+=8,byte_index++)
                {
                    unsigned char b=bytes[byte_index];
#pragma GCC unroll 8
                    for (unsigned char bit=0;bit<8;bit++)
                    {
                        u=u->p[(b>>bit)&1];
                        if (u->isLeaf())
                        {
                            out[outLen++]=(T)(u->c+tree.offset);
                            u=&tree.ht[tree.root];
                        }
                    }
                }
                if (bit_pos<len)
                {
                    unsigned char b=bytes[byte_index];
                    for (uint64_t bit=0;bit<len-bit_pos;bit++)
                    {
                        u=u->p[(b>>bit)&1];
                        if (u->isLeaf())
                        {
                            out[outLen++]=(T)(u->c+tree.offset);
                            u=&tree.ht[tree.root];
                        }
                    }
                }
                if (targetLength&&outLen!=targetLength)
                    throw runtime_error("Huffman payload length does not match its value count");
                bytes+=(len+7)>>3;
                return;
            }
            uint64_t outLen=0;
            uint64_t bit_pos=0;
            auto offset=tree.offset;
            uint64_t payload_bytes=(len+7)>>3;
            uint64_t table_mask=(1ull<<tree.decode_table_bits)-1;
            Node *zero_leaf=tree.ht[tree.root].p[0]->isLeaf()?tree.ht[tree.root].p[0]:nullptr;
            Node *one_leaf=tree.ht[tree.root].p[1]->isLeaf()?tree.ht[tree.root].p[1]:nullptr;

            while ((bit_pos>>3)+8<=payload_bytes&&bit_pos+tree.limit<=len)
            {
                unsigned char shift=bit_pos&7;
                uint64_t acc=bytesToInt64_littleEndian(bytes+(bit_pos>>3))>>shift;
                unsigned char available=64-shift;
                do
                {
                    if (targetLength&&outLen>=targetLength)
                        throw runtime_error("Huffman payload contains too many values");
                    Node *run_leaf=nullptr;
                    uint64_t run=0;
                    if (zero_leaf&&(acc&0xFF)==0)
                    {
                        run_leaf=zero_leaf;
                        run=acc?__builtin_ctzll(acc):64;
                    }
                    else if (one_leaf&&(acc&0xFF)==0xFF)
                    {
                        run_leaf=one_leaf;
                        uint64_t inv=~acc;
                        run=inv?__builtin_ctzll(inv):64;
                    }
                    if (run_leaf)
                    {
                        run=min<uint64_t>(run,available);
                        run=min<uint64_t>(run,len-bit_pos);
                        if (targetLength)
                            run=min<uint64_t>(run,targetLength-outLen);
                    }
                    if (run>=8)
                    {
                        fill(out+outLen,out+outLen+run,(T)(run_leaf->c+offset));
                        outLen+=run;
                        acc=run==64?0:acc>>run;
                        available-=run;
                        bit_pos+=run;
                        continue;
                    }
                    const typename HuffmanTree::DecodeEntry &entry=tree.decode_table[acc&table_mask];
                    if (entry.len)
                    {
                        out[outLen++]=entry.symbol;
                        acc>>=entry.len;
                        available-=entry.len;
                        bit_pos+=entry.len;
                    }
                    else
                    {
                        Node *u=entry.node;
                        acc>>=tree.decode_table_bits;
                        available-=tree.decode_table_bits;
                        bit_pos+=tree.decode_table_bits;
                        while (!u->isLeaf())
                        {
                            u=u->p[acc&1];
                            acc>>=1;
                            available--;
                            bit_pos++;
                        }
                        out[outLen++]=(T)(u->c+offset);
                    }
                } while (available>=tree.limit&&bit_pos+tree.limit<=len);
            }

            Node *u=&tree.ht[tree.root];
            while (bit_pos<len)
            {
                u=u->p[readBit(bytes,bit_pos++)];
                if (u->isLeaf())
                {
                    if (targetLength&&outLen>=targetLength)
                        throw runtime_error("Huffman payload contains too many values");
                    out[outLen++]=(T)(u->c+offset);
                    u=&tree.ht[tree.root];
                }
            }
            if (u!=&tree.ht[tree.root])
                throw runtime_error("Huffman payload ends inside a code");
            if (targetLength&&outLen!=targetLength)
                throw runtime_error("Huffman payload contains too few values");

            bytes+=(len+7)>>3;
        }

        void save(unsigned char*& c) 
        {
            saveAsDFSOrder(c);
        }

        void load(const unsigned char*& c)
        {
            loadAsDFSOrder(c);
        }

    private:
        inline void int64ToBytes_bigEndian(unsigned char *b,uint64_t num)
        {
            b[0]=static_cast<unsigned char>(num>>56);
            b[1]=static_cast<unsigned char>(num>>48);
            b[2]=static_cast<unsigned char>(num>>40);
            b[3]=static_cast<unsigned char>(num>>32);
            b[4]=static_cast<unsigned char>(num>>24);
            b[5]=static_cast<unsigned char>(num>>16);
            b[6]=static_cast<unsigned char>(num>>8);
            b[7]=static_cast<unsigned char>(num);
        }

        inline int64_t bytesToInt64_bigEndian(const unsigned char *b)
        {
            int64_t temp=0;
            int64_t res=0;

            res<<=8;
            temp=b[0]&0xff;
            res|=temp;

            res<<=8;
            temp=b[1]&0xff;
            res|=temp;

            res<<=8;
            temp=b[2]&0xff;
            res|=temp;

            res<<=8;
            temp=b[3]&0xff;
            res|=temp;

            res<<=8;
            temp=b[4]&0xff;
            res|=temp;

            res<<=8;
            temp=b[5]&0xff;
            res|=temp;

            res<<=8;
            temp=b[6]&0xff;
            res|=temp;

            res<<=8;
            temp=b[7]&0xff;
            res|=temp;

            return res;
        }

        inline uint64_t bytesToInt64_littleEndian(const unsigned char *b)
        {
            uint64_t res=0;
            for (uint64_t i=0;i<8;i++)
                res|=(uint64_t)b[i]<<(i<<3);
            return res;
        }

        static void writeBytesBit(unsigned char*& c,unsigned char val,unsigned char& mask,unsigned char& index) 
        {
            assert(val==0 || val==1);

            mask|=val<<index++;
            if (index==8) {
                *c++=mask;
                mask=index=0;
            }
        }

        static void writeBytes(unsigned char*& c,T val,unsigned char len,unsigned char& mask,unsigned char& index)
        {
            assert(len>=1 and len<=sizeof(T)*8);

            if (len+index>=8)
            {
                mask|=(val&((1<<(8-index))-1))<<index;
                val>>=8-index;
                len-=8-index;
                *c++=mask;
                mask=index=0;

                while (len >= 8)
                {
                    *c++=val&((1<<8)-1);
                    val>>=8;
                    len-=8;
                }
            }

            mask|=(val&((1<<len)-1))<<index;
            index+=len;
        }

        static void writeBytesByte(unsigned char*& c,unsigned char val)
        { 
            *c++=val;
        }

        static void writeBytesClearMask(unsigned char*& c,unsigned char& mask,unsigned char& index)
        {
            if (index>0)
                *c++=mask;
        }

        static unsigned char readBit(const unsigned char* const &c,int i)
        { 
            return ((*(c+(i>>3)))>>(i&7))&1;
        }

        void saveAsDFSOrder(unsigned char*& c)
        {
            unsigned char mask=0,index=0;

            writeBytesByte(c,(tree.usemp<<7)|((tree.n==1)<<6)|tree.mbft);
            uint64_t offset_bits=(uint64_t)(int64_t)tree.offset;
            for (uint64_t i=0;i<sizeof(int64_t);i++)
                *c++=(offset_bits>>(i<<3))&0xFF;
            int64ToBytes_bigEndian(c,tree.n);
            c+=sizeof(uint64_t);
            int64ToBytes_bigEndian(c,tree.maxval);
            c+=sizeof(uint64_t);

            if (tree.n==0 || tree.n==1)
            {
                writeBytesClearMask(c,mask,index);
                return;
            }

            std::stack<Node*> stk;

            stk.push(&tree.ht[tree.root]);

            while (!stk.empty())
            {
                Node* u=stk.top();
                stk.pop();
                if (u->isLeaf())
                {
                    writeBytesBit(c,0x01,mask,index);
                    writeBytes(c,u->c,tree.mbft,mask,index);
                }
                else
                {
                    writeBytesBit(c,0x00,mask,index);
                    stk.push(u->p[1]);
                    stk.push(u->p[0]);
                }
            }

            writeBytesClearMask(c,mask,index);
        }

        void loadAsDFSOrder(const unsigned char*& bytes)
        {
            tree.init();

            tree.usemp=(*bytes)>>7;
            tree.mbft=(*bytes)&0x3f;
            ++bytes;

            uint64_t offset_bits=0;
            for (uint64_t i=0;i<sizeof(int64_t);i++)
                offset_bits|=(uint64_t)*bytes++<<(i<<3);
            tree.offset=(T)(int64_t)offset_bits;

            tree.n=bytesToInt64_bigEndian(bytes);
            bytes+=sizeof(uint64_t);
            tree.ht.reserve(tree.n<<1);
            
            tree.maxval=bytesToInt64_bigEndian(bytes);
            bytes+=sizeof(uint64_t);
            if (tree.usemp==0x00)
                if (tree.n>0)
                {
                    tree.veccode.resize(tree.maxval);
                    tree.veclen.resize(tree.maxval);
                }
            if (tree.n==0)
            {
                tree.setConstructed();
                return;
            }

            if (tree.n==1)
            {
                tree.ht.resize(2);
                tree.root=0;
                tree.ht[0]=Node(0,&tree.ht[1]);
                tree.ht[1]=Node(0);
                if (tree.usemp)
                {
                    tree.mplen[0]=1;
                    tree.mpcode[0]=0;
                }
                else
                {
                    tree.veclen[0]=1;
                    tree.veccode[0]=0;
                }
                tree.setConstructed();
                return;
            }

            tree.root=0;
            tree.ht.push_back(Node());
            std::stack<Node*> stk;
            stk.push(&tree.ht[0]);
            uint64_t i=1;

            while (!stk.empty())
            {
                Node* u=stk.top();

                if (readBit(bytes,i++)==0x00)
                {
                    tree.ht.push_back(Node());
                    if (u->p[0]==nullptr)
                        u->p[0]=&tree.ht[tree.ht.size()-1];
                    else
                        u->p[1]=&tree.ht[tree.ht.size()-1];
                    stk.push(&tree.ht[tree.ht.size()-1]);
                }
                else
                {
                    T c=0;
                    for (int j=0;j<tree.mbft;j++)
                        c|=static_cast<T>(readBit(bytes,i++))<<j;
                    tree.ht.push_back(Node(c));
                    if (u->p[0]==nullptr)
                        u->p[0]=&tree.ht[tree.ht.size()-1];
                    else
                        u->p[1]=&tree.ht[tree.ht.size()-1];
                    while (!stk.empty() and stk.top()->p[1] != nullptr)
                        stk.pop();
                }
            }
            bytes+=(i+7)>>3;

            if (tree.usemp)
                tree.dfs_mp(&tree.ht[tree.root]);
            else
                tree.dfs_vec(&tree.ht[tree.root]);
            tree.buildDecodeTable();

            tree.setConstructed();
        }
};
