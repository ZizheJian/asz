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
    vector<double> rel_eb_vec={1e-6};

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

    vector<double> t2_list={0.4};
    // for (int t2_id=0;t2_id<=20;t2_id++)
    //     t2_list.push_back(0.2+t2_id*0.01);
    
    //////// 通过实际压缩来知道单点预测mse ////////
    // {
    //     for (double rel_eb:rel_eb_vec)
    //     {
    //         double abs_eb=rel_eb*(max_val-min_val);
    //         double neg_2_eb=1/(2*abs_eb);
    //         for (double t2:t2_list)
    //         {
    //             double mse=0,vars=0;
    //             vector<int64_t> qb_vec;
    //             qb_vec.reserve(compressed_data_num);
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
    //                         vars+=pow(pred-data[pos],2);
    //                     }
    //             double H2=get_H2(qb_vec);
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
    //             double cr=(double)(compressed_data_num*sizeof(float))/zstd_bs_len;
    //             double br=(8*sizeof(float))/cr;
    //             mse/=compressed_data_num;
    //             vars/=compressed_data_num;
    //             double psnr=10*log10(pow(max_val-min_val,2)/mse);
    //             printf("rel_eb=%e, t2=%f, BR=%f, H2=%f, PSNR=%f\n",rel_eb,t2,br,H2,psnr);
    //             printf("vars=%f\n",vars);
    //         }
    //     }
    // }

    //////// 单点预测涉及到的数据的协方差 ////////
    // {
    //     vector<vector<double>> sigmas(5,vector<double>(5));
    //     for (uint64_t i0=0;i0<data_shape[0];i0++)
    //         for (uint64_t i1=0;i1<data_shape[1];i1++)
    //         {
    //             float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
    //             for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //             {
    //                 sigmas[0][0]+=line[i2-3]*line[i2-3];
    //                 sigmas[0][1]+=line[i2-3]*line[i2-1];
    //                 sigmas[0][2]+=line[i2-3]*line[i2];
    //                 sigmas[0][3]+=line[i2-3]*line[i2+1];
    //                 sigmas[0][4]+=line[i2-3]*line[i2+3];
    //                 sigmas[1][1]+=line[i2-1]*line[i2-1];
    //                 sigmas[1][2]+=line[i2-1]*line[i2];
    //                 sigmas[1][3]+=line[i2-1]*line[i2+1];
    //                 sigmas[1][4]+=line[i2-1]*line[i2+3];
    //                 sigmas[2][2]+=line[i2]*line[i2];
    //                 sigmas[2][3]+=line[i2]*line[i2+1];
    //                 sigmas[2][4]+=line[i2]*line[i2+3];
    //                 sigmas[3][3]+=line[i2+1]*line[i2+1];
    //                 sigmas[3][4]+=line[i2+1]*line[i2+3];
    //                 sigmas[4][4]+=line[i2+3]*line[i2+3];
    //             }
    //         }
    //     for (uint64_t i=0;i<sigmas.size();i++)
    //         for (uint64_t j=i;j<sigmas[0].size();j++)
    //         {
    //             sigmas[i][j]/=compressed_data_num;
    //             sigmas[j][i]=sigmas[i][j];
    //         }
    //     for (uint64_t i=0;i<sigmas.size();i++)
    //     {
    //         printf("{");
    //         for (uint64_t j=0;j<sigmas[0].size();j++)
    //         {
    //             printf("%f",sigmas[i][j]);
    //             if (j<sigmas[0].size()-1)
    //                 printf(",");
    //         }
    //         printf("},\n");
    //     }
    // }

    //////// 通过实际压缩来知道两个相邻点的预测误差协方差（不考虑跨行的情况） ////////
    // {
    //     for (double rel_eb:rel_eb_vec)
    //     {
    //         double abs_eb=rel_eb*(max_val-min_val);
    //         double neg_2_eb=1/(2*abs_eb);
    //         for (double t2:t2_list)
    //         {
    //             vector<vector<double>> varj(2,vector<double>(2));
    //             for (uint64_t i0=0;i0<data_shape[0];i0++)
    //                 for (uint64_t i1=0;i1<data_shape[1];i1++)
    //                 {
    //                     vector<double> err_vec;
    //                     for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //                     {
    //                         uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                         double pred=(0.25-t2)*data[pos-3];
    //                         pred+=(0.25+t2)*data[pos-1];
    //                         pred+=(0.25+t2)*data[pos+1];
    //                         pred+=(0.25-t2)*data[pos+3];
    //                         err_vec.push_back(pred-data[pos]);
    //                     }
    //                     for (uint64_t i2=0;i2<(data_shape[2]-7)/2;i2++)
    //                     {
    //                         varj[0][0]+=err_vec[i2]*err_vec[i2];
    //                         varj[0][1]+=err_vec[i2]*err_vec[i2+1];
    //                         varj[1][1]+=err_vec[i2+1]*err_vec[i2+1];
    //                     }
    //                 }
    //             for (uint64_t i=0;i<varj.size();i++)
    //                 for (uint64_t j=i;j<varj[0].size();j++)
    //                 {
    //                     varj[i][j]/=(data_shape[0]*data_shape[1]*((data_shape[2]-7)/2));
    //                     printf("varj[%lu][%lu]=%f\n",i,j,varj[i][j]);
    //                 }
    //         }
    //     }
    // }

    //////// 双点预测涉及到的数据的协方差 ////////
    // {
    //     vector<vector<double>> sigmaj(7,vector<double>(7));
    //     for (uint64_t i0=0;i0<data_shape[0];i0++)
    //         for (uint64_t i1=0;i1<data_shape[1];i1++)
    //         {
    //             float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
    //             for (uint64_t i2=3;i2+5<data_shape[2];i2+=2)
    //             {
    //                 sigmaj[0][0]+=line[i2-3]*line[i2-3];
    //                 sigmaj[0][1]+=line[i2-3]*line[i2-1];
    //                 sigmaj[0][2]+=line[i2-3]*line[i2];
    //                 sigmaj[0][3]+=line[i2-3]*line[i2+1];
    //                 sigmaj[0][4]+=line[i2-3]*line[i2+2];
    //                 sigmaj[0][5]+=line[i2-3]*line[i2+3];
    //                 sigmaj[0][6]+=line[i2-3]*line[i2+5];
    //                 sigmaj[1][1]+=line[i2-1]*line[i2-1];
    //                 sigmaj[1][2]+=line[i2-1]*line[i2];
    //                 sigmaj[1][3]+=line[i2-1]*line[i2+1];
    //                 sigmaj[1][4]+=line[i2-1]*line[i2+2];
    //                 sigmaj[1][5]+=line[i2-1]*line[i2+3];
    //                 sigmaj[1][6]+=line[i2-1]*line[i2+5];
    //                 sigmaj[2][2]+=line[i2]*line[i2];
    //                 sigmaj[2][3]+=line[i2]*line[i2+1];
    //                 sigmaj[2][4]+=line[i2]*line[i2+2];
    //                 sigmaj[2][5]+=line[i2]*line[i2+3];
    //                 sigmaj[2][6]+=line[i2]*line[i2+5];
    //                 sigmaj[3][3]+=line[i2+1]*line[i2+1];
    //                 sigmaj[3][4]+=line[i2+1]*line[i2+2];
    //                 sigmaj[3][5]+=line[i2+1]*line[i2+3];
    //                 sigmaj[3][6]+=line[i2+1]*line[i2+5];
    //                 sigmaj[4][4]+=line[i2+2]*line[i2+2];
    //                 sigmaj[4][5]+=line[i2+2]*line[i2+3];
    //                 sigmaj[4][6]+=line[i2+2]*line[i2+5];
    //                 sigmaj[5][5]+=line[i2+3]*line[i2+3];
    //                 sigmaj[5][6]+=line[i2+3]*line[i2+5];
    //                 sigmaj[6][6]+=line[i2+5]*line[i2+5];
    //             }
    //         }
    //     for (uint64_t i=0;i<sigmaj.size();i++)
    //         for (uint64_t j=i;j<sigmaj[0].size();j++)
    //         {
    //             sigmaj[i][j]/=(data_shape[0]*data_shape[1]*((data_shape[2]-7)/2));
    //             sigmaj[j][i]=sigmaj[i][j];
    //         }
    //     for (uint64_t i=0;i<sigmaj.size();i++)
    //     {
    //         printf("{");
    //         for (uint64_t j=0;j<sigmaj[0].size();j++)
    //         {
    //             printf("%f",sigmaj[i][j]);
    //             if (j<sigmaj[0].size()-1)
    //                 printf(",");
    //         }
    //         printf("},\n");
    //     }
    // }

    //////// 生成单点预测误差，存储到文件中，后续用python处理 ////////
    {
        for (double rel_eb:rel_eb_vec)
        {
            double abs_eb=rel_eb*(max_val-min_val);
            double neg_2_eb=1/(2*abs_eb);
            for (double t2:t2_list)
            {
                double mse=0,vars=0;
                vector<double> pred_err_vec;
                pred_err_vec.reserve(compressed_data_num);
                for (uint64_t i0=0;i0<data_shape[0];i0++)
                    for (uint64_t i1=0;i1<data_shape[1];i1++)
                        for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
                        {
                            uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                            double pred=(0.25-t2)*data[pos-3];
                            pred+=(0.25+t2)*data[pos-1];
                            pred+=(0.25+t2)*data[pos+1];
                            pred+=(0.25-t2)*data[pos+3];
                            pred_err_vec.push_back(pred-data[pos]);
                        }
                ofstream ofs("pred_err_"+to_string(t2)+".bin",ios::binary);
                ofs.write(reinterpret_cast<char*>(pred_err_vec.data()),pred_err_vec.size()*sizeof(double));
                ofs.close();
            }
        }
    }

    //////// 计算H2和psnr ////////
    // {
    //     for (double rel_eb:rel_eb_vec)
    //     {
    //         double abs_eb=rel_eb*(max_val-min_val);
    //         double neg_2_eb=1/(2*abs_eb);
    //         for (double t2:t2_list)
    //         {
    //             double mse=0;
    //             vector<vector<int64_t>> qb_vec(data_shape[0]*data_shape[1],vector<int64_t>());
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
    //                         qb_vec[i0*data_shape[1]+i1].push_back(qb);
    //                         double decmp=pred-qb*2*abs_eb;
    //                         mse+=pow(decmp-data[pos],2);
    //                     }
    //             double H2=get_H2_line_seaparated(qb_vec);
    //             mse/=compressed_data_num;
    //             double psnr=10*log10(pow(max_val-min_val,2)/mse);
    //             printf("rel_eb=%e, t2=%f, H2=%f, PSNR=%f\n",rel_eb,t2,H2,psnr);
    //         }
    //     }
    // }
}