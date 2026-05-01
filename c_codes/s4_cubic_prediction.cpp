// 这个程序会把模拟不同方向和遍历顺序的三阶插值，把不同t2和rel_eb下的比特率、熵和PSNR记录到csv中
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

void compress_dot(vector<int64_t> &qb_vec,double &mse,vector<float> &data,vector<uint64_t> &data_shape,uint64_t adjacent_pos_dist,double abs_eb,double neg_2_eb,
    double t2,uint64_t i0,uint64_t i1,uint64_t i2)
{
    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    double pred=(0.25-t2)*(data[pos-3*adjacent_pos_dist]+data[pos+3*adjacent_pos_dist]);
    pred+=(0.25+t2)*(data[pos-1*adjacent_pos_dist]+data[pos+1*adjacent_pos_dist]);
    int64_t qb=llround((pred-data[pos])*neg_2_eb);
    qb_vec.push_back(qb);
    double decmp=pred-qb*2*abs_eb;
    mse+=pow(decmp-data[pos],2);
}

void compress(vector<float> &data,vector<uint64_t> &data_shape,string &csv_path,double max_val,double min_val,vector<double> &rel_eb_vec,uint64_t stride,string predictor)
{
    string temp_csv_path=csv_path.substr(0,csv_path.size()-4)+"_"+predictor+".csv";
    uint64_t compressed_data_num=0,adjacent_pos_dist=0;
    if (predictor.compare(0,6,"cubic0")==0)
    {
        adjacent_pos_dist=data_shape[1]*data_shape[2];
        if (predictor=="cubic0_120")
        {
            compressed_data_num=(data_shape[0]-5)/2;
            compressed_data_num*=(data_shape[1]+stride-1)/stride;
            compressed_data_num*=(data_shape[2]+stride-1)/stride;
        }
        else if (predictor=="cubic0_021")
        {
            compressed_data_num=(data_shape[0]+2*stride-7)/(2*stride);
            compressed_data_num*=data_shape[1];
            compressed_data_num*=(data_shape[2]+stride-1)/stride;
        }
        else if (predictor=="cubic0_012")
        {
            compressed_data_num=(data_shape[0]+2*stride-7)/(2*stride);
            compressed_data_num*=(data_shape[1]+stride-1)/stride;
            compressed_data_num*=data_shape[2];
        }
    }
    else if (predictor.compare(0,6,"cubic1")==0)
    {
        adjacent_pos_dist=data_shape[2];
        if (predictor=="cubic1_120")
        {
            compressed_data_num=data_shape[0];
            compressed_data_num*=(data_shape[1]+2*stride-7)/(2*stride);
            compressed_data_num*=(data_shape[2]+stride-1)/stride;
        }
        else if (predictor=="cubic1_021")
        {
            compressed_data_num=(data_shape[0]+stride-1)/stride;
            compressed_data_num*=(data_shape[1]-5)/2;
            compressed_data_num*=(data_shape[2]+stride-1)/stride;
        }
        else if (predictor=="cubic1_012")
        {
            compressed_data_num=(data_shape[0]+stride-1)/stride;
            compressed_data_num*=(data_shape[1]+2*stride-7)/(2*stride);
            compressed_data_num*=data_shape[2];
        }        
    }
    else if (predictor.compare(0,6,"cubic2")==0)
    {
        adjacent_pos_dist=1;
        if (predictor=="cubic2_120")
        {
            compressed_data_num=data_shape[0];
            compressed_data_num*=(data_shape[1]+stride-1)/stride;
            compressed_data_num*=(data_shape[2]+2*stride-7)/(2*stride);
        }
        else if (predictor=="cubic2_021")
        {
            compressed_data_num=(data_shape[0]+stride-1)/stride;
            compressed_data_num*=data_shape[1];
            compressed_data_num*=(data_shape[2]+2*stride-7)/(2*stride);
        }
        else if (predictor=="cubic2_012")
        {
            compressed_data_num=(data_shape[0]+stride-1)/stride;
            compressed_data_num*=(data_shape[1]+stride-1)/stride;
            compressed_data_num*=(data_shape[2]-5)/2;
        }
    }
    string br_name=stride==1?"BR":"BR_s"+to_string(stride);
    string h1_name=stride==1?"H1":"H1_s"+to_string(stride);
    string h2_name=stride==1?"H2":"H2_s"+to_string(stride);
    string psnr_name=stride==1?"PSNR":"PSNR_s"+to_string(stride);
    add_column(temp_csv_path,"rel_eb");
    add_column(temp_csv_path,"t2");
    add_column(temp_csv_path,br_name);
    add_column(temp_csv_path,h1_name);
    add_column(temp_csv_path,h2_name);
    add_column(temp_csv_path,psnr_name);
    vector<double> t2_vec;
    for (int i=14;i<=22;i++)
        t2_vec.push_back((float)i/64);
    for (double rel_eb:rel_eb_vec)
    {
        double abs_eb=rel_eb*(max_val-min_val);
        double neg_2_eb=1/(2*abs_eb);
        for (double t2:t2_vec)
        {
            double mse=0;
            vector<int64_t> qb_vec;
            qb_vec.reserve(compressed_data_num);
            if (predictor=="cubic0_120")
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i0=3;i0+3<data_shape[0];i0+=2)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic0_021")
                for (uint64_t i0=3;i0+3<data_shape[0];i0+=2*stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic0_012")
                for (uint64_t i0=3;i0+3<data_shape[0];i0+=2*stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic1_120")
                for (uint64_t i1=3;i1+3<data_shape[1];i1+=2*stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic1_021")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i1=3;i1+3<data_shape[1];i1+=2)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic1_012")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i1=3;i1+3<data_shape[1];i1+=2*stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic2_120")
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic2_021")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="cubic2_012")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                    compress_dot(qb_vec,mse,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            if (qb_vec.size()!=compressed_data_num)
                throw runtime_error(predictor+" qb_vec.size()!=compressed_data_num");
            double H1=get_H1(qb_vec);
            double H2=get_H2(qb_vec);
            vector<unsigned char> huffman_bs_vec(compressed_data_num*sizeof(float)*2);
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
            add_row(temp_csv_path,rel_eb,t2);
            write_value(temp_csv_path,rel_eb,t2,br_name,br);
            write_value(temp_csv_path,rel_eb,t2,h1_name,H1);
            write_value(temp_csv_path,rel_eb,t2,h2_name,H2);
            write_value(temp_csv_path,rel_eb,t2,psnr_name,psnr);
            printf("rel_eb=%f, t2=%f\n",rel_eb,t2);
            printf("BR=%f, CR=%f\n",br,cr);
            printf("H1=%f, H1_cr=%f\n",H1,(8*sizeof(float))/(H1));
            printf("H2=%f, H2_cr=%f\n",H2,(8*sizeof(float))/(H2));
            printf("PSNR=%f\n",psnr);
            printf("\n");
        }
    }
}

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

    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Miranda/density.f32.dat";
    vector<uint64_t> data_shape={256,384,384};
    vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6};
    string csv_path="/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32_center.bin";
    // vector<uint64_t> data_shape={256,256,256};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_Nyx_baryon_density_center.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/SCALE_LETKF/PRES-98x1200x1200.dat_center.bin";
    // vector<uint64_t> data_shape={49,600,600};
    // vector<double> rel_eb_vec={1e-1,1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/results_cubic_prediction_LETKF_center.csv";

    uint64_t stride=16;

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

    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic0_120");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic0_021");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic0_012");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic1_120");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic1_021");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic1_012");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic2_120");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic2_021");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"cubic2_012");
}