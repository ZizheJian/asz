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
    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    // vector<uint64_t> data_shape={100,500,500};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,5.623e-5,3.162e-5,1.778e-5,1e-5,5.623e-6,3.162e-6,1.778e-6,1e-6,1e-7,1e-8};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_ISABEL_Pf01.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/9-ID_CSSI_data/benchmarkdata/Avg_L0470_Double_exp_elong_siemens_1p00sampit_0p05inplane_patch1_of1_part0_001.h5.f32_center.bin";
    // vector<uint64_t> data_shape={150,454,390};
    // vector<double> rel_eb_vec={1e-1,5.623e-2,3.162e-2,1.778e-2,1e-2,5.623e-3,3.162e-3,1.778e-3,1e-3};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_CSSI_L0470_center.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32_center.bin";
    // vector<uint64_t> data_shape={205,312,363};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,5.623e-3,3.162e-3,1.778e-3,1e-4};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_APSU_004_center.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat_center.bin";
    // vector<uint64_t> data_shape={13,900,1800};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_CLDICE_center.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Miranda/density.f32.dat";
    // vector<uint64_t> data_shape={256,384,384};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_Miranda.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32_center.bin";
    // vector<uint64_t> data_shape={256,256,256};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_Nyx_baryon_density_center.csv";

    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/SCALE_LETKF/PRES-98x1200x1200.dat_center.bin";
    vector<uint64_t> data_shape={49,600,600};
    vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_LETKF_center.csv";

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
    
    add_column(csv_path,"rel_eb");
    add_column(csv_path,"t2");
    add_column(csv_path,"BR");
    add_column(csv_path,"H1");
    add_column(csv_path,"H2");
    add_column(csv_path,"H3");
    add_column(csv_path,"H4");
    add_column(csv_path,"PSNR");
    vector<double> t2_vec;
    for (int i=0;i<=20;i++)
        t2_vec.push_back(0.2+i*0.01);
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
            add_row(csv_path,rel_eb,t2);
            write_value(csv_path,rel_eb,t2,"BR",br);
            write_value(csv_path,rel_eb,t2,"H1",H1);
            write_value(csv_path,rel_eb,t2,"H2",H2);
            write_value(csv_path,rel_eb,t2,"H3",H3);
            write_value(csv_path,rel_eb,t2,"H4",H4);
            write_value(csv_path,rel_eb,t2,"PSNR",psnr);
            printf("rel_eb=%f, t2=%f\n",rel_eb,t2);
            printf("BR=%f, CR=%f\n",br,cr);
            printf("H1=%f, H1_cr=%f\n",H1,(8*sizeof(float))/(H1));
            printf("H2=%f, H2_cr=%f\n",H2,(8*sizeof(float))/(H2));
            printf("H3=%f, H3_cr=%f\n",H3,(8*sizeof(float))/(H3));
            printf("H4=%f, H4_cr=%f\n",H4,(8*sizeof(float))/(H4));
            printf("PSNR=%f\n",psnr);
            printf("\n");
        }
    }
}