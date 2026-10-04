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
#include "../third_party/csv_tools/c_codes/csv.hpp"
#include "../third_party/zstd/lib/zstd.h"

using namespace std;
using namespace csv_tools;

void lossless_encode_and_write_csv(string &temp_csv_path,uint64_t stride,vector<int64_t> &qb_vec,double max_val,double min_val,
    double rel_eb,vector<double> &t_vec,double mse,double pred_rmse,double pred_mae);

void compress_1d4r_dot(vector<int64_t> &qb_vec,double &mse,double &pred_rmse,double &pred_mae,vector<float> &data,
    vector<uint64_t> &data_shape,vector<uint64_t> &adjacent_pos_dist_vec,double abs_eb,double neg_2_eb,vector<double> t_vec,
    uint64_t i0,uint64_t i1,uint64_t i2)
{
    uint64_t adjacent_pos_dist=adjacent_pos_dist_vec[0];
    double t=t_vec[0];
    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    double pred=(0.25-t)*(data[pos-3*adjacent_pos_dist]+data[pos+3*adjacent_pos_dist]);
    pred+=(0.25+t)*(data[pos-adjacent_pos_dist]+data[pos+adjacent_pos_dist]);
    pred_rmse+=pow(pred-data[pos],2);
    pred_mae+=fabs(pred-data[pos]);
    int64_t qb=llround((pred-data[pos])*neg_2_eb);
    qb_vec.push_back(qb);
    double decmp=pred-qb*2*abs_eb;
    mse+=pow(decmp-data[pos],2);
}

void compress_2d4r_dot(vector<int64_t> &qb_vec,double &mse,double &pred_rmse,double &pred_mae,vector<float> &data,
    vector<uint64_t> &data_shape,vector<uint64_t> &adjacent_pos_dist_vec,double abs_eb,double neg_2_eb,vector<double> t_vec,
    uint64_t i0,uint64_t i1,uint64_t i2)
{
    uint64_t adjacent_pos_dist1=adjacent_pos_dist_vec[0];
    uint64_t adjacent_pos_dist2=adjacent_pos_dist_vec[1];
    double t=t_vec[0];
    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    double pred=(0.25+t)*(data[pos-adjacent_pos_dist1]+data[pos+adjacent_pos_dist1]);
    pred+=(0.25-t)*(data[pos-adjacent_pos_dist2]+data[pos+adjacent_pos_dist2]);
    pred_rmse+=pow(pred-data[pos],2);
    pred_mae+=fabs(pred-data[pos]);
    int64_t qb=llround((pred-data[pos])*neg_2_eb);
    qb_vec.push_back(qb);
    double decmp=pred-qb*2*abs_eb;
    mse+=pow(decmp-data[pos],2);
}

void compress_1d6r_dot(vector<int64_t> &qb_vec,double &mse,double &pred_rmse,double &pred_mae,vector<float> &data,
    vector<uint64_t> &data_shape,vector<uint64_t> &adjacent_pos_dist_vec,double abs_eb,double neg_2_eb,vector<double> t_vec,
    uint64_t i0,uint64_t i1,uint64_t i2)
{
    uint64_t adjacent_pos_dist=adjacent_pos_dist_vec[0];
    double t1=t_vec[0];
    double t2=t_vec[1];
    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    double pred=(1.0/6-t1)*(data[pos-5*adjacent_pos_dist]+data[pos+5*adjacent_pos_dist]);
    pred+=(1.0/6-t2)*(data[pos-3*adjacent_pos_dist]+data[pos+3*adjacent_pos_dist]);
    pred+=(1.0/6+t1+t2)*(data[pos-adjacent_pos_dist]+data[pos+adjacent_pos_dist]);
    pred_rmse+=pow(pred-data[pos],2);
    pred_mae+=fabs(pred-data[pos]);
    int64_t qb=llround((pred-data[pos])*neg_2_eb);
    qb_vec.push_back(qb);
    double decmp=pred-qb*2*abs_eb;
    mse+=pow(decmp-data[pos],2);
}

void compress(vector<float> &data,vector<uint64_t> &data_shape,string &csv_path,double max_val,double min_val,
    vector<double> &rel_eb_vec,uint64_t stride,string predictor)
{
    string temp_csv_path=csv_path.substr(0,csv_path.size()-4)+"_"+predictor+".csv";
    vector<uint64_t> adjacent_pos_dist_vec;
    if ((predictor.starts_with("1d4r0")) || (predictor.starts_with("1d6r0")))
        adjacent_pos_dist_vec.push_back(data_shape[1]*data_shape[2]);
    else if ((predictor.starts_with("1d4r1")) || (predictor.starts_with("1d6r1")))
        adjacent_pos_dist_vec.push_back(data_shape[2]);
    else if ((predictor.starts_with("1d4r2")) || (predictor.starts_with("1d6r2")))
        adjacent_pos_dist_vec.push_back(1);
    else if (predictor.starts_with("2d4r01"))
    {
        adjacent_pos_dist_vec.push_back(data_shape[1]*data_shape[2]);
        adjacent_pos_dist_vec.push_back(data_shape[2]);
    }
    else if (predictor.starts_with("2d4r02"))
    {
        adjacent_pos_dist_vec.push_back(data_shape[1]*data_shape[2]);
        adjacent_pos_dist_vec.push_back(1);
    }
    else if (predictor.starts_with("2d4r12"))
    {
        adjacent_pos_dist_vec.push_back(data_shape[2]);
        adjacent_pos_dist_vec.push_back(1);
    }
    else
        throw runtime_error("没见过的predictor");
    if ((predictor.starts_with("1d4r")) || (predictor.starts_with("2d4r")))
        create_csv_header(temp_csv_path,"rel_eb","t1");
    else if (predictor.starts_with("1d6r"))
        create_csv_header(temp_csv_path,"rel_eb","t1","t2");
    for (double rel_eb:rel_eb_vec)
    {
        double abs_eb=rel_eb*(max_val-min_val);
        double neg_2_eb=1/(2*abs_eb);
        if (predictor.starts_with("1d4r"))
        {
            vector<vector<double>> t_vec_vec;
            for (int i=0;i<=12;i++)
                t_vec_vec.push_back({(float)i/32});
            for (vector<double> &t_vec:t_vec_vec)
            {
                double mse=0,pred_rmse=0,pred_mae=0;
                vector<int64_t> qb_vec;
                qb_vec.reserve(data_shape[0]*data_shape[1]*data_shape[2]);
                if (predictor=="1d4r0_xx0")
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i0=3;i0+3<data_shape[0];i0+=2)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r0_xx1")
                    for (uint64_t i0=3;i0+3<data_shape[0];i0+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r0_xx2")
                    for (uint64_t i0=3;i0+3<data_shape[0];i0+=2*stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r1_xx0")
                    for (uint64_t i1=3;i1+3<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r1_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=3;i1+3<data_shape[1];i1+=2)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r1_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=3;i1+3<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r2_xx0")
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r2_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=3;i2+3<data_shape[2];i2+=2*stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r2_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                lossless_encode_and_write_csv(temp_csv_path,stride,qb_vec,max_val,min_val,rel_eb,t_vec,
                    mse,pred_rmse,pred_mae);
            }
        }
        else if (predictor.starts_with("2d4r"))
        {
            vector<vector<double>> t_vec_vec;
            for (int i=-6;i<=6;i++)
                t_vec_vec.push_back({(float)i/24});
            for (vector<double> &t_vec:t_vec_vec)
            {
                double mse=0,pred_rmse=0,pred_mae=0;
                vector<int64_t> qb_vec;
                qb_vec.reserve(data_shape[0]*data_shape[1]*data_shape[2]);
                if (predictor=="2d4r01_xx0")
                    for (uint64_t i1=1;i1+1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i0=1;i0+1<data_shape[0];i0+=2)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r01_xx1")
                    for (uint64_t i0=1;i0+1<data_shape[0];i0+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=1;i1+1<data_shape[1];i1+=1)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r01_xx2")
                    for (uint64_t i0=1;i0+1<data_shape[0];i0+=2*stride)
                    for (uint64_t i1=1;i1+1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r02_xx0")
                    for (uint64_t i1=0;i1<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=1;i2+1<data_shape[2];i2+=stride)
                    for (uint64_t i0=1;i0+1<data_shape[0];i0+=1)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r02_xx1")
                    for (uint64_t i0=1;i0+1<data_shape[0];i0+=stride)
                    for (uint64_t i2=1;i2+1<data_shape[2];i2+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=2)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r02_xx2")
                    for (uint64_t i0=1;i0+1<data_shape[0];i0+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=1;i2+1<data_shape[2];i2+=1)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r12_xx0")
                    for (uint64_t i1=1;i1+1<data_shape[1];i1+=stride)
                    for (uint64_t i2=1;i2+1<data_shape[2];i2+=2*stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r12_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=1;i2+1<data_shape[2];i2+=2*stride)
                    for (uint64_t i1=1;i1+1<data_shape[1];i1+=1)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="2d4r12_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=1;i1+1<data_shape[1];i1+=stride)
                    for (uint64_t i2=1;i2+1<data_shape[2];i2+=2)
                        compress_2d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                lossless_encode_and_write_csv(temp_csv_path,stride,qb_vec,max_val,min_val,rel_eb,t_vec,
                    mse,pred_rmse,pred_mae);
            }
        }
        else if (predictor.starts_with("1d6r"))
        {
            vector<vector<double>> t_vec_vec;
            for (auto i1:{0,11,22,31,41})
            for (auto i2:{0,113,248,341,453,567,680,793})
                t_vec_vec.push_back({(float)i1/186,(float)i2/1488});
            for (vector<double> &t_vec:t_vec_vec)
            {
                double mse=0,pred_rmse=0,pred_mae=0;
                vector<int64_t> qb_vec;
                qb_vec.reserve(data_shape[0]*data_shape[1]*data_shape[2]);
                if (predictor=="1d6r0_xx0")
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i0=5;i0+5<data_shape[0];i0+=2)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r0_xx1")
                    for (uint64_t i0=5;i0+5<data_shape[0];i0+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r0_xx2")
                    for (uint64_t i0=5;i0+5<data_shape[0];i0+=2*stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r1_xx0")
                    for (uint64_t i1=5;i1+5<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r1_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=5;i1+5<data_shape[1];i1+=2)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r1_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=5;i1+5<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r2_xx0")
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=5;i2+5<data_shape[2];i2+=2*stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r2_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=5;i2+5<data_shape[2];i2+=2*stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d6r2_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=5;i2+5<data_shape[2];i2+=2)
                        compress_1d6r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                lossless_encode_and_write_csv(temp_csv_path,stride,qb_vec,max_val,min_val,rel_eb,t_vec,
                    mse,pred_rmse,pred_mae);
            }
        }
    }
}

void lossless_encode_and_write_csv(string &temp_csv_path,uint64_t stride,vector<int64_t> &qb_vec,
    double max_val,double min_val,double rel_eb,vector<double> &t_vec,double mse,double pred_rmse,double pred_mae)
{
    string br_name=stride==1?"BR":"BR_s"+to_string(stride);
    string h1_name=stride==1?"H1":"H1_s"+to_string(stride);
    string pred_rmse_name=stride==1?"RMSE":"RMSE_s"+to_string(stride);
    string pred_mae_name=stride==1?"MAE":"MAE_s"+to_string(stride);
    string psnr_name=stride==1?"PSNR":"PSNR_s"+to_string(stride);
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
    pred_rmse=sqrt(pred_rmse/qb_vec.size());
    pred_mae/=qb_vec.size();
    double psnr=10*log10(pow(max_val-min_val,2)/mse);
    if (t_vec.size()==1)
        printf("rel_eb=%f, t1=%f\n",rel_eb,t_vec[0]);
    else if (t_vec.size()==2)
        printf("rel_eb=%f, t1=%f, t2=%f\n",rel_eb,t_vec[0],t_vec[1]);
    printf("BR=%f, CR=%f\n",br,cr);
    printf("H1=%f, H1_cr=%f\n",H1,(8*sizeof(float))/(H1));
    printf("RMSE=%f, MAE=%f\n",pred_rmse,pred_mae);
    printf("PSNR=%f\n",psnr);
    printf("\n");
    vector<double> query_row_key;
    query_row_key.push_back(rel_eb);
    query_row_key.insert(query_row_key.end(),t_vec.begin(),t_vec.end());
    write_csv_item(temp_csv_path,query_row_key,br_name,br);
    write_csv_item(temp_csv_path,query_row_key,h1_name,H1);
    write_csv_item(temp_csv_path,query_row_key,pred_rmse_name,pred_rmse);
    write_csv_item(temp_csv_path,query_row_key,pred_mae_name,pred_mae);
    write_csv_item(temp_csv_path,query_row_key,psnr_name,psnr);
}

int main()
{
    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/P/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    vector<double> rel_eb_vec={1e-2,1e-3,1e-4,1e-5,1e-6};
    string csv_path="/home/x-zjian1/asz/csv/Pf01.csv";

    // string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat";
    // vector<uint64_t> data_shape={26,1800,3600};
    // vector<double> rel_eb_vec={1e-2,1e-3,1e-4,1e-5,1e-6};
    // string csv_path="/home/x-zjian1/asz/csv/CLDICE.csv";

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

    vector<string> predictor_vec;
    
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
