#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>

#include "huffman.hpp"
#include "csv_tools/csv.hpp"
#include "third_party/zstd/lib/zstd.h"

using namespace std;

int main()
{
    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    vector<float> rel_eb_vec={1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};

    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();

    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);

    string csv_path="/home/x-zjian1/ASTZ_tests/results_linear_coefficient_enumerating.csv";
    add_column(csv_path,"REL_EB");
    for (float rel_eb:rel_eb_vec)
    {
        for (int t1_int=-10;t1_int<=10;t1_int++)
        {
            float t1=0.5+t1_int*0.01;
            float abs_eb=rel_eb*(max_val-min_val);
            float neg_2_eb=1/(2*abs_eb);
            uint64_t compressed_data_size=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);
            float mse=0;
            vector<int64_t> qb_vec;
            qb_vec.reserve(compressed_data_size);
            for (uint64_t i0=0;i0<data_shape[0];i0++)
                for (uint64_t i1=0;i1<data_shape[1];i1++)
                    for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                    {
                        uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                        float pred=t1*data[pos-1]+(1-t1)*data[pos+1];
                        int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
                        qb_vec.push_back(qb);
                        float decmp=pred-qb*2*abs_eb;
                        mse+=pow(decmp-data[pos],2);
                    }
            vector<unsigned char> huffman_bs_vec(data_size*sizeof(float));
            unsigned char *huffman_bs=huffman_bs_vec.data();
            huffman_encoder_class<int64_t> huffman_encoder;
            huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
            huffman_encoder.save(huffman_bs);
            huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
            uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
            uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
            vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
            uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
            zstd_bs_vec.resize(zstd_bs_len);
            float cr=(float)(compressed_data_size*sizeof(float))/zstd_bs_len;
            float br=(8*sizeof(float))/cr;
            mse/=compressed_data_size;
            float psnr=10*log10(pow(max_val-min_val,2)/mse);
            add_row(csv_path,rel_eb);
            add_column(csv_path,change_string_type(t1)+"_BR");
            add_column(csv_path,change_string_type(t1)+"_PSNR");
            add_value(csv_path,rel_eb,change_string_type(t1)+"_BR",br);
            add_value(csv_path,rel_eb,change_string_type(t1)+"_PSNR",psnr);
            printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
        }
    }
}