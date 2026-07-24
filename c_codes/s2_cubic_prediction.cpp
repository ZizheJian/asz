// 这个程序会把模拟不同方向和遍历顺序的预测，把不同t和rel_eb下的比特率、熵和PSNR记录到csv中
// 1d4r预测公式是：
//      err=(0.25-t1)*(data[-3]+data[3])+(0.25+t1)*(data[-1]+data[1])-data[0]
// 2d4r预测公式是：
//      err=(0.25+t1)*(data[-1,0]+data[1,0])+(0.25-t1)*(data[0,-1]+data[0,1])-data[0]
// 1d6r预测公式是：
//      err=(1/6-t1)*(data[-5]+data[5])+(1/6-t2)*(data[-3]+data[3])+(1/6+t1+t2)*(data[-1]+data[1])-data[0]

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

void compress_dot(vector<int64_t> &qb_vec,double &mse,double &pred_mse,double &pred_mae,vector<float> &data,vector<uint64_t> &data_shape,
    uint64_t adjacent_pos_dist,double abs_eb,double neg_2_eb,double t2,uint64_t i0,uint64_t i1,uint64_t i2)
{
    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    double pred=(0.25-t2)*(data[pos-3*adjacent_pos_dist]+data[pos+3*adjacent_pos_dist]);
    pred+=(0.25+t2)*(data[pos-1*adjacent_pos_dist]+data[pos+1*adjacent_pos_dist]);
    pred_mse+=pow(pred-data[pos],2);
    pred_mae+=fabs(pred-data[pos]);
    int64_t qb=llround((pred-data[pos])*neg_2_eb);
    qb_vec.push_back(qb);
    double decmp=pred-qb*2*abs_eb;
    mse+=pow(decmp-data[pos],2);
}

void compress(vector<float> &data,vector<uint64_t> &data_shape,string &csv_path,double max_val,double min_val,vector<double> &rel_eb_vec,
    uint64_t stride,string predictor)
{
    string temp_csv_path=csv_path.substr(0,csv_path.size()-4)+"_"+predictor+".csv";
    vector<uint64_t> adjacent_pos_dist;
    if ((predictor.compare(0,5,"1d4r0")==0) || (predictor.compare(0,5,"1d6r0")==0))
        adjacent_pos_dist.push_back(data_shape[1]*data_shape[2]);
    else if ((predictor.compare(0,5,"1d4r1")==0) || (predictor.compare(0,5,"1d6r1")==0))
        adjacent_pos_dist.push_back(data_shape[2]);
    else if ((predictor.compare(0,5,"1d4r2")==0) || (predictor.compare(0,5,"1d6r2")==0))
        adjacent_pos_dist.push_back(1);
    else if (predictor.compare(0,5,"2d4r01")==0)
    {
        adjacent_pos_dist.push_back(data_shape[1]*data_shape[2]);
        adjacent_pos_dist.push_back(data_shape[2]);
    }
    else if (predictor.compare(0,5,"2d4r02")==0)
    {
        adjacent_pos_dist.push_back(data_shape[1]*data_shape[2]);
        adjacent_pos_dist.push_back(1);
    }
    else if (predictor.compare(0,5,"2d4r12")==0)
    {
        adjacent_pos_dist.push_back(data_shape[2]);
        adjacent_pos_dist.push_back(1);
    }
    else
        throw runtime_error("unknown predictor");
    string br_name=stride==1?"BR":"BR_s"+to_string(stride);
    string h1_name=stride==1?"H1":"H1_s"+to_string(stride);
    string h2_name=stride==1?"H2":"H2_s"+to_string(stride);
    string pred_mse_name=stride==1?"MSE":"MSE_s"+to_string(stride);
    string pred_mae_name=stride==1?"MAE":"MAE_s"+to_string(stride);
    string psnr_name=stride==1?"PSNR":"PSNR_s"+to_string(stride);
    add_column(temp_csv_path,"rel_eb");
    add_column(temp_csv_path,"t1");
    add_column(temp_csv_path,"t2");
    add_column(temp_csv_path,br_name);
    add_column(temp_csv_path,h1_name);
    add_column(temp_csv_path,pred_mse_name);
    add_column(temp_csv_path,pred_mae_name);
    add_column(temp_csv_path,psnr_name);
    vector<double> t2_vec;
    for (int i=0;i<=12;i++)
        t2_vec.push_back((float)i/32);
    for (double rel_eb:rel_eb_vec)
    {
        double abs_eb=rel_eb*(max_val-min_val);
        double neg_2_eb=1/(2*abs_eb);
        for (double t2:t2_vec)
        {
            double mse=0;
            double pred_mse=0,pred_mae=0;
            vector<int64_t> qb_vec;
            qb_vec.reserve(data_shape[0]*data_shape[1]*data_shape[2]);
            if (predictor=="1d4r0_xx0")
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i0=3;i0+3<data_shape[0];i0+=2)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r0_xx1")
                for (uint64_t i0=3;i0+3<data_shape[0];i0+=2*stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r0_xx2")
                for (uint64_t i0=3;i0+3<data_shape[0];i0+=2*stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r1_xx0")
                for (uint64_t i1=3;i1+3<data_shape[1];i1+=2*stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r1_xx1")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                for (uint64_t i1=3;i1+3<data_shape[1];i1+=2)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r1_xx2")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i1=3;i1+3<data_shape[1];i1+=2*stride)
                for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r2_xx0")
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r2_xx1")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            else if (predictor=="1d4r2_xx2")
                for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                    compress_dot(qb_vec,mse,pred_mse,pred_mae,data,data_shape,adjacent_pos_dist,abs_eb,neg_2_eb,t2,i0,i1,i2);
            double H1=get_H1(qb_vec);
            vector<unsigned char> huffman_bs_vec(qb_vec.size()*sizeof(float));
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
            double cr=(double)(qb_vec.size()*sizeof(float))/zstd_bs_len;
            double br=(8*sizeof(float))/cr;
            mse/=qb_vec.size();
            pred_mse/=qb_vec.size();
            pred_mae/=qb_vec.size();
            double psnr=10*log10(pow(max_val-min_val,2)/mse);
            add_row(temp_csv_path,rel_eb,t2);
            write_value(temp_csv_path,rel_eb,t2,br_name,br);
            write_value(temp_csv_path,rel_eb,t2,h1_name,H1);
            write_value(temp_csv_path,rel_eb,t2,pred_mse_name,pred_mse);
            write_value(temp_csv_path,rel_eb,t2,pred_mae_name,pred_mae);
            write_value(temp_csv_path,rel_eb,t2,psnr_name,psnr);
            printf("rel_eb=%f, t2=%f\n",rel_eb,t2);
            printf("BR=%f, CR=%f\n",br,cr);
            printf("H1=%f, H1_cr=%f\n",H1,(8*sizeof(float))/(H1));
            printf("MSE=%f, MAE=%f\n",pred_mse,pred_mae);
            printf("PSNR=%f\n",psnr);
            printf("\n");
        }
    }
}

int main()
{
    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    // vector<uint64_t> data_shape={100,500,500};
    // vector<double> rel_eb_vec={1e-2,1e-3,1e-4,1e-5,1e-6};
    // string csv_path="/home/x-zjian1/ASTZ_tests/csv/Pf01.csv";

    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat";
    vector<uint64_t> data_shape={26,1800,3600};
    vector<double> rel_eb_vec={1e-2,1e-3,1e-4,1e-5,1e-6};
    string csv_path="/home/x-zjian1/ASTZ_tests/csv/CLDICE.csv";

    uint64_t stride=1;

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

    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r0_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r0_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r0_xx2");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r1_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r1_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r1_xx2");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r2_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r2_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d4r2_xx2");

    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r01_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r01_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r01_xx2");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r02_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r02_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r02_xx2");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r12_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r12_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"2d4r12_xx2");

    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r0_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r0_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r0_xx2");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r1_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r1_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r1_xx2");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r2_xx0");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r2_xx1");
    compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,"1d6r2_xx2");
}