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
#include <chrono>
#include <filesystem>
#include <limits>

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

vector<vector<double>> six_reference_grid(const string &mode)
{
    if (mode=="transition")
    {
        // 三类端点：六点等权、五次插值、13组1D4R；再加入不同类别之间的中点。
        vector<vector<double>> grid={{0,0},{119.0/768,203.0/768}};
        for (int i=0;i<=12;i++)
            grid.push_back({1.0/6,(3*i-8)/96.0});
        grid.push_back({119.0/1536,203.0/1536});
        for (int i=0;i<=12;i++)
        {
            grid.push_back({1.0/12,(3*i-8)/192.0});
            grid.push_back({247.0/1536,(24*i+139)/1536.0});
        }
        return grid;
    }
    vector<vector<double>> grid;
    for (auto i1:{0,11,22,31,41})
    for (auto i2:{0,113,248,341,453,567,680,793})
        grid.push_back({(float)i1/186,(float)i2/1488});
    if (mode=="augmented")
    {
        // 保留旧网格，补入精确五次插值和全部1D4R候选；近似重复点替换为精确系数。
        vector<vector<double>> exact={{119.0/768,203.0/768}};
        for (int i=0;i<=12;i++)
            exact.push_back({1.0/6,i/32.0-1.0/12});
        for (const auto &candidate:exact)
        {
            auto match=find_if(grid.begin(),grid.end(),[&](const auto &point){return fabs(point[0]-candidate[0])<1e-7&&fabs(point[1]-candidate[1])<1e-7;});
            if (match==grid.end())
                grid.push_back(candidate);
            else
                *match=candidate;
        }
    }
    return grid;
}

void compress(vector<float> &data,vector<uint64_t> &data_shape,string &csv_path,double max_val,double min_val,
    vector<double> &rel_eb_vec,uint64_t stride,string predictor,const string &six_grid,bool shared_1d)
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
            uint64_t margin=shared_1d?5:3;
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
                    for (uint64_t i0=margin;i0+margin<data_shape[0];i0+=2)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r0_xx1")
                    for (uint64_t i0=margin;i0+margin<data_shape[0];i0+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r0_xx2")
                    for (uint64_t i0=margin;i0+margin<data_shape[0];i0+=2*stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r1_xx0")
                    for (uint64_t i1=margin;i1+margin<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r1_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=stride)
                    for (uint64_t i1=margin;i1+margin<data_shape[1];i1+=2)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r1_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=margin;i1+margin<data_shape[1];i1+=2*stride)
                    for (uint64_t i2=0;i2<data_shape[2];i2+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r2_xx0")
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=margin;i2+margin<data_shape[2];i2+=2*stride)
                    for (uint64_t i0=0;i0<data_shape[0];i0+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r2_xx1")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i2=margin;i2+margin<data_shape[2];i2+=2*stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=1)
                        compress_1d4r_dot(qb_vec,mse,pred_rmse,pred_mae,data,data_shape,adjacent_pos_dist_vec,abs_eb,neg_2_eb,
                            t_vec,i0,i1,i2);
                else if (predictor=="1d4r2_xx2")
                    for (uint64_t i0=0;i0<data_shape[0];i0+=stride)
                    for (uint64_t i1=0;i1<data_shape[1];i1+=stride)
                    for (uint64_t i2=margin;i2+margin<data_shape[2];i2+=2)
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
            auto t_vec_vec=six_reference_grid(six_grid);
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
    auto encode_start=chrono::steady_clock::now();
    if (qb_vec.empty())
        throw runtime_error("no prediction targets");
    string br_name=stride==1?"BR":"BR_s"+to_string(stride);
    string h1_name=stride==1?"H1":"H1_s"+to_string(stride);
    string pred_rmse_name=stride==1?"RMSE":"RMSE_s"+to_string(stride);
    string pred_mae_name=stride==1?"MAE":"MAE_s"+to_string(stride);
    string psnr_name=stride==1?"PSNR":"PSNR_s"+to_string(stride);
    double H1=get_H1(qb_vec);
    vector<unsigned char> huffman_bs_vec(qb_vec.size()*16+65536);
    unsigned char *huffman_bs=huffman_bs_vec.data();
    huffman_encoder_class<int64_t> huffman_encoder;
    huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
    huffman_encoder.save(huffman_bs);
    huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
    uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
    uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
    vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
    uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
    if (ZSTD_isError(zstd_bs_len))
        throw runtime_error(ZSTD_getErrorName(zstd_bs_len));
    zstd_bs_vec.resize(zstd_bs_len);
    double encode_seconds=chrono::duration<double>(chrono::steady_clock::now()-encode_start).count();
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
    write_csv_item(temp_csv_path,query_row_key,"SAMPLES",to_string(qb_vec.size()));
    write_csv_item(temp_csv_path,query_row_key,"ENCODE_SECONDS",encode_seconds);
}

int main(int argc,char **argv)
try
{
    if (argc==2&&string(argv[1])=="--help")
    {
        printf("usage: s2_many_prediction input dim0 dim1 dim2 output_prefix [1d4r|2d4r|1d6r|all [eb0,eb1,... [legacy|augmented|transition [legacy|shared1d]]]]\n");
        return 0;
    }
    if (argc!=1&&(argc<6||argc>10))
        throw runtime_error("use --help for arguments");
    auto started=chrono::steady_clock::now();
    string data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/P/Pf01.bin";
    vector<uint64_t> data_shape={100,500,500};
    vector<double> rel_eb_vec={1e-2,1e-3,1e-4,1e-5,1e-6};
    string output_prefix="/home/x-zjian1/asz/csv/Pf01",family="all";
    if (argc>=6)
    {
        data_path=argv[1];
        for (int axis=0;axis<3;axis++)
            data_shape[axis]=stoull(argv[axis+2]);
        output_prefix=argv[5];
    }
    if (argc>=7)
        family=argv[6];
    if (argc>=8)
    {
        rel_eb_vec.clear();
        stringstream bounds(argv[7]);
        string bound;
        while (getline(bounds,bound,','))
            rel_eb_vec.push_back(stod(bound));
    }
    if (family!="all"&&family!="1d4r"&&family!="2d4r"&&family!="1d6r")
        throw runtime_error("unknown predictor family");
    string six_grid=argc>=9?argv[8]:"legacy";
    if (six_grid!="legacy"&&six_grid!="augmented"&&six_grid!="transition")
        throw runtime_error("six-reference grid must be legacy, augmented or transition");
    string targets=argc>=10?argv[9]:"legacy";
    if (targets!="legacy"&&targets!="shared1d")
        throw runtime_error("target mode must be legacy or shared1d");
    printf("six_reference_grid=%s, candidates=%zu, targets=%s\n",six_grid.c_str(),six_reference_grid(six_grid).size(),targets.c_str());
    if (rel_eb_vec.empty())
        throw runtime_error("error-bound grid is empty");
    for (double bound:rel_eb_vec)
        if (!isfinite(bound)||bound<=0)
            throw runtime_error("error bounds must be positive and finite");
    vector<string> predictor_vec;
    for (string stencil:{"1d4r0","1d4r1","1d4r2","2d4r01","2d4r02","2d4r12","1d6r0","1d6r1","1d6r2"})
        if (family=="all"||stencil.starts_with(family))
            for (int order=0;order<3;order++)
                predictor_vec.push_back(stencil+"_xx"+to_string(order));
    for (const auto &predictor:predictor_vec)
        if (filesystem::exists(output_prefix+"_"+predictor+".csv"))
            throw runtime_error("output already exists; use a fresh output prefix");
    auto parent=filesystem::path(output_prefix).parent_path();
    if (!parent.empty())
        filesystem::create_directories(parent);
    string csv_path=output_prefix+".csv";
    // stride>1会随遍历顺序改变采样集合，因此不开放该选项；shared1d统一四点与六点的边界。
    uint64_t stride=1;
    uint64_t data_size=1;
    for (uint64_t dimension:data_shape)
    {
        if (dimension<12||data_size>numeric_limits<uint64_t>::max()/dimension)
            throw runtime_error("invalid dimensions; each dimension must be at least 12");
        data_size*=dimension;
    }
    if (data_size>numeric_limits<uint64_t>::max()/sizeof(float)||filesystem::file_size(data_path)!=data_size*sizeof(float))
        throw runtime_error("input size does not match float32 dimensions");
    vector<float> data;
    data.resize(data_size);
    ifstream data_file(data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
    if (!data_file)
        throw runtime_error("input read failed");
    data_file.close();
    for (float value:data)
        if (!isfinite(value))
            throw runtime_error("input contains nonfinite values");
    float min_val=*min_element(data.begin(),data.end());
    float max_val=*max_element(data.begin(),data.end());
    printf("min_val=%f\n",min_val);
    printf("max_val=%f\n",max_val);
    if (!(max_val>min_val))
        throw runtime_error("constant input");
    for (const auto &predictor:predictor_vec)
    {
        auto predictor_start=chrono::steady_clock::now();
        compress(data,data_shape,csv_path,max_val,min_val,rel_eb_vec,stride,predictor,six_grid,targets=="shared1d");
        printf("predictor=%s, elapsed_seconds=%.6f\n",predictor.c_str(),chrono::duration<double>(chrono::steady_clock::now()-predictor_start).count());
    }
    printf("total_seconds=%.6f\n",chrono::duration<double>(chrono::steady_clock::now()-started).count());
    return 0;
}
catch (const exception &error)
{
    fprintf(stderr,"error: %s\n",error.what());
    return 1;
}
