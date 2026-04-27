// 这个程序会把模拟三阶插值，把不同t2和rel_eb下的比特率、熵和PSNR记录到csv/results_cubic_prediction.csv文件中
// 预测公式是：
//      err=(0.25-3*t1-t2+t3)*data[-3]+(0.25-t1+t2-t3)*data[-1]-data[0]+(0.25+t1+t2+t3)*data[1]+(0.25+3*t1-t2-t3)*data[3]
// 这里我们直接设定t1和t3都是0

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
    string data_path="/lcrc/project/SDR/zjian-in-SDR/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    string csv_path="/home/zjian/ASTZ_tests/csv/results_cubic_prediction_dim3_ISABEL_Pf01.csv";

    uint64_t data_size=data_shape[0]*data_shape[1]*data_shape[2];
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    data_file.close();
    uint64_t compressed_data_num=(data_shape[0])*(data_shape[1])*((data_shape[2]-5)/2);

    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);
    
    add_column(csv_path,"rel_eb");
    add_column(csv_path,"t2");
    add_column(csv_path,"BR");
    add_column(csv_path,"PSNR");
    vector<double> t2_vec;
    for (int i=24;i<=48;i++)
        t2_vec.push_back((float)i/128);
    for (double rel_eb:rel_eb_vec)
    {
        double abs_eb=rel_eb*(max_val-min_val);
        double neg_2_eb=1/(2*abs_eb);
        for (double t2:t2_vec)
        {
            double mse=0;
            vector<int64_t> qb_vec;
            qb_vec.reserve(compressed_data_num);
            for (uint64_t i0=0;i0<data_shape[0];i0++)
                for (uint64_t i1=0;i1<data_shape[1];i1++)
                    for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                    {
                        uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                        double pred=(0.25-t2)*data[pos-3];
                        pred+=(0.25+t2)*data[pos-1];
                        pred+=(0.25+t2)*data[pos+1];
                        pred+=(0.25-t2)*data[pos+3];
                        int64_t qb=llround((pred-data[pos])*neg_2_eb);
                        qb_vec.push_back(qb);
                        double decmp=pred-qb*2*abs_eb;
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
            double cr=(double)(compressed_data_num*sizeof(float))/zstd_bs_len;
            double br=(8*sizeof(float))/cr;
            mse/=compressed_data_num;
            double psnr=10*log10(pow(max_val-min_val,2)/mse);
            add_row(csv_path,rel_eb,t2);
            write_value(csv_path,rel_eb,t2,"BR",br);
            write_value(csv_path,rel_eb,t2,"PSNR",psnr);
            printf("rel_eb=%f, t2=%f\n",rel_eb,t2);
            printf("BR=%f, CR=%f\n",br,cr);
            printf("PSNR=%f\n",psnr);
            printf("\n");
        }
    }
}