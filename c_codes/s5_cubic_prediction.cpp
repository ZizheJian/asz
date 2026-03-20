// 发现在不同eb下，各种H的趋势并不总是和实际比特率一致，但至少有一条是一致的。
// 当rel_eb=1e-1时，实际比特率大致是H2加一个常数。
// 当rel_eb=1e-3时，H2在实际比特率左右，比较接近，但H1的趋势和实际比特率更相似。
// 当rel_eb=1e-8时，实际比特率超过了H1。
// 另外还要验证直接用H当做比特率，或者用zero-rate估算比特率时能否找出最好的t2。
// 然后尝试根据数据的协方差估算bins的压缩误差的分布。

#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>

#include "huffman.hpp"
#include "get_H.hpp"
#include "csv_tools/csv.hpp"
#include "third_party/zstd/lib/zstd.h"

using namespace std;

int main()
{
    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,5.623e-5,3.162e-5,1.778e-5,1e-5,5.623e-6,3.162e-6,1.778e-6,1e-6,1e-7,1e-8};

    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();
    uint64_t compressed_data_num=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);

    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);
    
    // double base_br1=0.338714838;
    // double base_psnr1=88.0984802246;
    // double base_br2=8.3692502975;
    // double base_psnr2=138.8479614258;
    // double k=(base_br2-base_br1)/(base_psnr2-base_psnr1);
    string csv_path="/home/x-zjian1/ASTZ_tests/results_cubic_prediction.csv";
    add_column(csv_path,"t2");
    double t1=0,t2=0,t3=0;
    for (double rel_eb:rel_eb_vec)
    {
        double abs_eb=rel_eb*(max_val-min_val);
        double neg_2_eb=1/(2*abs_eb);
        for (int t2_int=-10;t2_int<=10;t2_int++)
        {
            t2=0.3+t2_int*0.01;
            double mse=0;
            vector<int64_t> qb_vec;
            qb_vec.reserve(compressed_data_num);
            for (uint64_t i0=0;i0<data_shape[0];i0++)
                for (uint64_t i1=0;i1<data_shape[1];i1++)
                    for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                    {
                        uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                        double pred=(0.25-3*t1-t2+t3)*data[pos-3];
                        pred+=(0.25-t1+t2-t3)*data[pos-1];
                        pred+=(0.25+t1+t2+t3)*data[pos+1];
                        pred+=(0.25+3*t1-t2-t3)*data[pos+3];
                        int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
                        qb_vec.push_back(qb);
                        double decmp=pred-qb*2*abs_eb;
                        mse+=pow(decmp-data[pos],2);
                    }
            double H1=get_H1(qb_vec);
            double H2=get_H2(qb_vec);
            double H3=get_H3(qb_vec);
            double H4=get_H4(qb_vec);
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
            double cr=(double)(compressed_data_num*sizeof(float))/zstd_bs_len;
            double br=(8*sizeof(float))/cr;
            mse/=compressed_data_num;
            double psnr=10*log10(pow(max_val-min_val,2)/mse);
            add_row(csv_path,change_string_type(t2));
            add_column(csv_path,change_string_type(rel_eb)+"_BR");
            add_column(csv_path,change_string_type(rel_eb)+"_H1");
            add_column(csv_path,change_string_type(rel_eb)+"_H2");
            add_column(csv_path,change_string_type(rel_eb)+"_H3");
            add_column(csv_path,change_string_type(rel_eb)+"_H4");
            add_value(csv_path,change_string_type(t2),change_string_type(rel_eb)+"_BR",change_string_type(br));
            add_value(csv_path,change_string_type(t2),change_string_type(rel_eb)+"_H1",change_string_type(H1));
            add_value(csv_path,change_string_type(t2),change_string_type(rel_eb)+"_H2",change_string_type(H2));
            add_value(csv_path,change_string_type(t2),change_string_type(rel_eb)+"_H3",change_string_type(H3));
            add_value(csv_path,change_string_type(t2),change_string_type(rel_eb)+"_H4",change_string_type(H4));
            printf("rel_eb=%f, t2=%f\n",rel_eb,t2);
            printf("H1=%f, H1_cr=%f\n",H1,(8*sizeof(float))/(H1));
            printf("H2=%f, H2_cr=%f\n",H2,(8*sizeof(float))/(H2));
            printf("H3=%f, H3_cr=%f\n",H3,(8*sizeof(float))/(H3));
            printf("H4=%f, H4_cr=%f\n",H4,(8*sizeof(float))/(H4));
            // printf("estimated_J=%f\n",H1-k*psnr);
            printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
            // printf("actual_J=%f\n",br-k*psnr);
            printf("\n");
        }
    }
}