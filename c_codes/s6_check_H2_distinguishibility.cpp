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
    double sampling_rate=2;

    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();
    // uint64_t compressed_data_num=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);

    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);

    // {
    //     string csv_path="/home/x-zjian1/ASTZ_tests/results_cubic_prediction.csv";
    //     add_column(csv_path,"rel_eb");
    //     add_column(csv_path,"t2");
    //     add_column(csv_path,"BR");
    //     add_column(csv_path,"PSNR");
    //     vector<double> t2_list;
    //     for (int t2_id=0;t2_id<=20;t2_id++)
    //         t2_list.push_back(0.2+t2_id*0.01);
    //     for (double rel_eb:rel_eb_vec)
    //     {
    //         double abs_eb=rel_eb*(max_val-min_val);
    //         double neg_2_eb=1/(2*abs_eb);
    //         for (double t2:t2_list)
    //         {
    //             double mse=0;
    //             vector<int64_t> qb_vec;
    //             for (uint64_t i0=0;i0<data_shape[0];i0++)
    //                 for (uint64_t i1=0;i1<data_shape[1];i1++)
    //                     for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //                     {
    //                         uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                         double pred=(0.25-t2)*data[pos-3];
    //                         pred+=(0.25+t2)*data[pos-1];
    //                         pred+=(0.25+t2)*data[pos+1];
    //                         pred+=(0.25-t2)*data[pos+3];
    //                         int64_t qb=(int64_t)llround((pred-data[pos])*neg_2_eb);
    //                         qb_vec.push_back(qb);
    //                         double decmp=pred-qb*2*abs_eb;
    //                         mse+=pow(decmp-data[pos],2);
    //                     }
    //             vector<unsigned char> huffman_bs_vec(data_size*sizeof(float));
    //             unsigned char *huffman_bs=huffman_bs_vec.data();
    //             huffman_encoder_class<int64_t> huffman_encoder;
    //             huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
    //             huffman_encoder.save(huffman_bs);
    //             huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
    //             uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
    //             uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
    //             vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
    //             uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
    //             zstd_bs_vec.resize(zstd_bs_len);
    //             double cr=(double)(qb_vec.size()*sizeof(float))/zstd_bs_len;
    //             double br=(8*sizeof(float))/cr;
    //             mse/=qb_vec.size();
    //             double psnr=10*log10(pow(max_val-min_val,2)/mse);
    //             printf("rel_eb=%e, t2=%f, BR=%f, PSNR=%f\n",rel_eb,t2,br,psnr);
    //             add_row(csv_path,change_string_type(rel_eb),change_string_type(t2));
    //             write_value(csv_path,change_string_type(rel_eb),change_string_type(t2),"BR",change_string_type(br));
    //             write_value(csv_path,change_string_type(rel_eb),change_string_type(t2),"PSNR",change_string_type(psnr));
    //         }
    //     }
    // }

    {
        int stride=64;
        string csv_path="/home/x-zjian1/ASTZ_tests/results_cubic_prediction_H2_stride64.csv";
        add_column(csv_path,"rel_eb");
        add_column(csv_path,"t2");
        add_column(csv_path,"H2");
        add_column(csv_path,"PSNR");
        vector<double> t2_list;
        for (int t2_id=0;t2_id<=20;t2_id++)
            t2_list.push_back(0.2+t2_id*0.01);
        for (double rel_eb:rel_eb_vec)
        {
            double abs_eb=rel_eb*(max_val-min_val);
            double neg_2_eb=1/(2*abs_eb);
            for (double t2:t2_list)
            {
                double mse=0;
                vector<int64_t> qb_vec;
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                        for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                        {
                            uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                            double pred=(0.25-t2)*data[pos-3];
                            pred+=(0.25+t2)*data[pos-1];
                            pred+=(0.25+t2)*data[pos+1];
                            pred+=(0.25-t2)*data[pos+3];
                            int64_t qb=(int64_t)llround((pred-data[pos])*neg_2_eb);
                            qb_vec.push_back(qb);
                            double decmp=pred-qb*2*abs_eb;
                            mse+=pow(decmp-data[pos],2);
                        }
                double H2=get_H2(qb_vec);
                mse/=qb_vec.size();
                double psnr=10*log10(pow(max_val-min_val,2)/mse);
                printf("rel_eb=%e, t2=%f, H2=%f, PSNR=%f\n",rel_eb,t2,H2,psnr);
                add_row(csv_path,change_string_type(rel_eb),change_string_type(t2));
                write_value(csv_path,change_string_type(rel_eb),change_string_type(t2),"H2",change_string_type(H2));
                write_value(csv_path,change_string_type(rel_eb),change_string_type(t2),"PSNR",change_string_type(psnr));
            }
        }
    }
}