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

    double base_br1=0.338714838;
    double base_psnr1=88.0984802246;
    double base_br2=8.3692502975;
    double base_psnr2=138.8479614258;
    double k=(base_br2-base_br1)/(base_psnr2-base_psnr1);
    string csv_path="/home/x-zjian1/ASTZ_tests/results_cubic_coefficient_enumerating.csv";
    add_column(csv_path,"REL_EB");
    float t1=0,t2=0,t3=0;
    for (float rel_eb:rel_eb_vec)
    {
        for (int t2_int=-10;t2_int<=10;t2_int++)
        {
            uint64_t p0=0;
            double p0_mse=0;
            t2=0.3+t2_int*0.01;
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
                        float pred=(0.25-3*t1-t2+t3)*data[pos-3];
                        pred+=(0.25-t1+t2-t3)*data[pos-1];
                        pred+=(0.25+t1+t2+t3)*data[pos+1];
                        pred+=(0.25+3*t1-t2-t3)*data[pos+3];
                        int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
                        if (qb==0)
                        {
                            p0++;
                            p0_mse+=pow(pred-data[pos],2);
                        }
                        qb_vec.push_back(qb);
                        float decmp=pred-qb*2*abs_eb;
                        mse+=pow(decmp-data[pos],2);
                    }
            map<int64_t,uint64_t> qb_freq;
            for (int64_t qb:qb_vec)
                qb_freq[qb]++;
            uint64_t total_qb_num=0;
            for (auto &[qb,freq]:qb_freq)
                total_qb_num+=freq;
            double discrete_entropy=0;
            for (auto &[qb,freq]:qb_freq)
            {
                double prob=(double)freq/total_qb_num;
                discrete_entropy-=prob*log2(prob);
            }
            p0_mse/=p0;
            double estimated_mse=(p0*p0_mse+(qb_vec.size()-p0)*abs_eb*abs_eb/3)/qb_vec.size();
            double estimated_psnr=10*log10(pow(max_val-min_val,2)/estimated_mse);
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
            add_column(csv_path,change_string_type(t2)+"_BR");
            add_column(csv_path,change_string_type(t2)+"_PSNR");
            add_value(csv_path,rel_eb,change_string_type(t2)+"_BR",br);
            add_value(csv_path,rel_eb,change_string_type(t2)+"_PSNR",psnr);
            printf("rel_eb=%f, t2=%f\n",rel_eb,t2);
            printf("min_bitrate=%f\n",discrete_entropy);
            printf("max_cr=%f, estimated_psnr=%f\n",(8*sizeof(float))/(discrete_entropy),estimated_psnr);
            printf("estimated_J=%f\n",discrete_entropy-k*estimated_psnr);
            printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
            printf("actual_J=%f\n",br-k*psnr);
            printf("\n");
        }
    }
}