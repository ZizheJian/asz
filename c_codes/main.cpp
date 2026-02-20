#include <string>
#include <vector>
#include <fstream>

#include "huffman.hpp"

using namespace std;

int main()
{
    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    float abs_eb=1e-4;
    float neg_2_eb=1/(2*abs_eb);

    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();

    //////// linear interpolation ////////
    {
        vector<int64_t> qb;
        qb.reserve(data_size);
        for (uint64_t i0=0;i0<data_shape[0];i0++)
            for (uint64_t i1=0;i1<data_shape[1];i1++)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                {
                    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                    float pred=(data[pos-1]+data[pos+1])/2;
                    qb.push_back(static_cast<int64_t>((pred-data[pos])*neg_2_eb));
                }
        vector<unsigned char> huffman_bs_vec(data_size*sizeof(float));
        unsigned char *huffman_bs=huffman_bs_vec.data();
        huffman_encoder_class<int64_t> huffman_encoder;
        huffman_encoder.preprocess_encode(qb.data(),qb.size());
        huffman_encoder.save(huffman_bs);
        huffman_encoder.encode(qb.data(),qb.size(),huffman_bs);
        uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
        
    }

}