#include <string>
#include <vector>
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

    //////// linear interpolation ////////
    // {
    //     string csv_path="/home/x-zjian1/ASTZ_tests/results_linear.csv";
    //     add_column(csv_path,"REL_EB");
    //     for (float rel_eb:rel_eb_vec)
    //     {
    //         float abs_eb=rel_eb*(max_val-min_val);
    //         float neg_2_eb=1/(2*abs_eb);
    //         uint64_t compressed_data_size=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);
    //         float mse=0;
    //         vector<int64_t> qb_vec;
    //         qb_vec.reserve(compressed_data_size);
    //         for (uint64_t i0=0;i0<data_shape[0];i0++)
    //             for (uint64_t i1=0;i1<data_shape[1];i1++)
    //                 for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //                 {
    //                     uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                     float pred=(data[pos-1]+data[pos+1])/2;
    //                     int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
    //                     qb_vec.push_back(qb);
    //                     float decmp=pred-qb*2*abs_eb;
    //                     mse+=pow(decmp-data[pos],2);
    //                 }
    //         vector<unsigned char> huffman_bs_vec(data_size*sizeof(float));
    //         unsigned char *huffman_bs=huffman_bs_vec.data();
    //         huffman_encoder_class<int64_t> huffman_encoder;
    //         huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
    //         huffman_encoder.save(huffman_bs);
    //         huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
    //         uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
    //         uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
    //         vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
    //         uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
    //         zstd_bs_vec.resize(zstd_bs_len);
    //         float cr=(float)(compressed_data_size*sizeof(float))/zstd_bs_len;
    //         float br=(8*sizeof(float))/cr;
    //         mse/=compressed_data_size;
    //         float psnr=10*log10(pow(max_val-min_val,2)/mse);
    //         add_row(csv_path,rel_eb);
    //         add_column(csv_path,"BR");
    //         add_column(csv_path,"PSNR");
    //         add_value(csv_path,rel_eb,"BR",br);
    //         add_value(csv_path,rel_eb,"PSNR",psnr);
    //         printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
    //     }
    // }

    //////// cubic interpolation ////////
    // {
    //     string csv_path="/home/x-zjian1/ASTZ_tests/results_cubic.csv";
    //     add_column(csv_path,"REL_EB");
    //     for (float rel_eb:rel_eb_vec)
    //     {
    //         float abs_eb=rel_eb*(max_val-min_val);
    //         float neg_2_eb=1/(2*abs_eb);
    //         uint64_t compressed_data_size=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);
    //         float mse=0;
    //         vector<int64_t> qb_vec;
    //         qb_vec.reserve(compressed_data_size);
    //         for (uint64_t i0=0;i0<data_shape[0];i0++)
    //             for (uint64_t i1=0;i1<data_shape[1];i1++)
    //                 for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //                 {
    //                     uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                     float pred=(-data[pos-3]+9*data[pos-1]+9*data[pos+1]-data[pos+3])/16;
    //                     int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
    //                     qb_vec.push_back(qb);
    //                     float decmp=pred-qb*2*abs_eb;
    //                     mse+=pow(decmp-data[pos],2);
    //                 }
    //         vector<unsigned char> huffman_bs_vec(data_size*sizeof(float));
    //         unsigned char *huffman_bs=huffman_bs_vec.data();
    //         huffman_encoder_class<int64_t> huffman_encoder;
    //         huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
    //         huffman_encoder.save(huffman_bs);
    //         huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
    //         uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
    //         uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
    //         vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
    //         uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
    //         zstd_bs_vec.resize(zstd_bs_len);
    //         float cr=(float)(compressed_data_size*sizeof(float))/zstd_bs_len;
    //         float br=(8*sizeof(float))/cr;
    //         mse/=compressed_data_size;
    //         float psnr=10*log10(pow(max_val-min_val,2)/mse);
    //         add_row(csv_path,rel_eb);
    //         add_column(csv_path,"BR");
    //         add_column(csv_path,"PSNR");
    //         add_value(csv_path,rel_eb,"BR",br);
    //         add_value(csv_path,rel_eb,"PSNR",psnr);
    //         printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
    //     }
    // }

    //////// linear interpolation with coefficient tuning ////////
    // {
    //     string csv_path="/home/x-zjian1/ASTZ_tests/results_linear_tune.csv";
    //     add_column(csv_path,"REL_EB");
    //     for (float rel_eb:rel_eb_vec)
    //     {
    //         for (int t1_int=-10;t1_int<=10;t1_int++)
    //         {
    //             float t1=0.5+t1_int*0.01;
    //             float abs_eb=rel_eb*(max_val-min_val);
    //             float neg_2_eb=1/(2*abs_eb);
    //             uint64_t compressed_data_size=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);
    //             float mse=0;
    //             vector<int64_t> qb_vec;
    //             qb_vec.reserve(compressed_data_size);
    //             for (uint64_t i0=0;i0<data_shape[0];i0++)
    //                 for (uint64_t i1=0;i1<data_shape[1];i1++)
    //                     for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //                     {
    //                         uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                         float pred=t1*data[pos-1]+(1-t1)*data[pos+1];
    //                         int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
    //                         qb_vec.push_back(qb);
    //                         float decmp=pred-qb*2*abs_eb;
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
    //             float cr=(float)(compressed_data_size*sizeof(float))/zstd_bs_len;
    //             float br=(8*sizeof(float))/cr;
    //             mse/=compressed_data_size;
    //             float psnr=10*log10(pow(max_val-min_val,2)/mse);
    //             add_row(csv_path,rel_eb);
    //             add_column(csv_path,change_string_type(t1)+"_BR");
    //             add_column(csv_path,change_string_type(t1)+"_PSNR");
    //             add_value(csv_path,rel_eb,change_string_type(t1)+"_BR",br);
    //             add_value(csv_path,rel_eb,change_string_type(t1)+"_PSNR",psnr);
    //             printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
    //         }
    //     }
    // }

    //////// cubic interpolation with coefficient tuning ////////
    // {
    //     string csv_path="/home/x-zjian1/ASTZ_tests/results_cubic_tune.csv";
    //     add_column(csv_path,"REL_EB");
    //     float t1=0,t2=0,t3=0;
    //     for (float rel_eb:rel_eb_vec)
    //     {
    //         for (int t2_int=-10;t2_int<=10;t2_int++)
    //         {
    //             float t2=0.3+t2_int*0.01;
    //             float abs_eb=rel_eb*(max_val-min_val);
    //             float neg_2_eb=1/(2*abs_eb);
    //             uint64_t compressed_data_size=data_shape[0]*data_shape[1]*((data_shape[2]-5)/2);
    //             float mse=0;
    //             vector<int64_t> qb_vec;
    //             qb_vec.reserve(compressed_data_size);
    //             for (uint64_t i0=0;i0<data_shape[0];i0++)
    //                 for (uint64_t i1=0;i1<data_shape[1];i1++)
    //                     for (uint64_t i2=3;i2+3<data_shape[2];i2+=2)
    //                     {
    //                         uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                         float pred=(0.25-3*t1-t2+t3)*data[pos-3];
    //                         pred+=(0.25-t1+t2-t3)*data[pos-1];
    //                         pred+=(0.25+t1+t2+t3)*data[pos+1];
    //                         pred+=(0.25+3*t1-t2-t3)*data[pos+3];
    //                         int64_t qb=static_cast<int64_t>((pred-data[pos])*neg_2_eb);
    //                         qb_vec.push_back(qb);
    //                         float decmp=pred-qb*2*abs_eb;
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
    //             float cr=(float)(compressed_data_size*sizeof(float))/zstd_bs_len;
    //             float br=(8*sizeof(float))/cr;
    //             mse/=compressed_data_size;
    //             float psnr=10*log10(pow(max_val-min_val,2)/mse);
    //             add_row(csv_path,rel_eb);
    //             add_column(csv_path,change_string_type(t2)+"_BR");
    //             add_column(csv_path,change_string_type(t2)+"_PSNR");
    //             add_value(csv_path,rel_eb,change_string_type(t2)+"_BR",br);
    //             add_value(csv_path,rel_eb,change_string_type(t2)+"_PSNR",psnr);
    //             printf("\033[91mcr=%f, br=%f, psnr=%f\n\033[0m",cr,br,psnr);
    //         }
    //     }
    // }

    //////// Solve phi1 and phi2 under AR(2) assumption ////////
    // {
    //     double s01=0,s02=0,s11=0,s12=0,s22=0;
    //     for (uint64_t i0=0;i0<data_shape[0];i0++)
    //         for (uint64_t i1=0;i1<data_shape[1];i1++)
    //         {
    //             float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
    //             double sigma_i_data=0,sigma_data=0;
    //             for (uint64_t i2=0;i2<data_shape[2];i2++)
    //             {
    //                 sigma_i_data+=i2*line[i2];
    //                 sigma_data+=line[i2];
    //             }
    //             double sigma_i=(data_shape[2]-1)*data_shape[2]/2;
    //             double sigma_i2=(data_shape[2]-1)*data_shape[2]*(2*data_shape[2]-1)/6;
    //             double a=(data_shape[2]*sigma_i_data-sigma_i*sigma_data)/(data_shape[2]*sigma_i2-sigma_i*sigma_i);
    //             double b=(sigma_i*sigma_i_data-sigma_i2*sigma_data)/(sigma_i*sigma_i-data_shape[2]*sigma_i2);
    //             vector<double> line2(data_shape[2]);
    //             for (uint64_t i2=0;i2<data_shape[2];i2++)
    //                 line2[i2]=line[i2]-a*i2-b;
    //             double local_s01=0,local_s02=0,local_s11=0,local_s12=0,local_s22=0;
    //             for (uint64_t i2=2;i2<data_shape[2];i2++)
    //             {
    //                 local_s01+=line2[i2]*line2[i2-1];
    //                 local_s02+=line2[i2]*line2[i2-2];
    //                 local_s11+=line2[i2-1]*line2[i2-1];
    //                 local_s12+=line2[i2-1]*line2[i2-2];
    //                 local_s22+=line2[i2-2]*line2[i2-2];
    //             }
    //             s01+=local_s01;
    //             s02+=local_s02;
    //             s11+=local_s11;
    //             s12+=local_s12;
    //             s22+=local_s22;
    //         }
        
    //     double phi1=(s01*s22-s02*s12)/(s11*s22-s12*s12);
    //     double phi2=(s02*s11-s01*s12)/(s11*s22-s12*s12);
    //     printf("phi1=%f, phi2=%f\n",phi1,phi2);
    // }

    //////// Solve l under SE assumption ////////
    // {
    //     vector<double> cov(11);
    //     for (uint64_t i0=0;i0<data_shape[0];i0++)
    //         for (uint64_t i1=0;i1<data_shape[1];i1++)
    //         {
    //             float *line=data.data()+i0*data_shape[1]*data_shape[2]+i1*data_shape[2];
    //             double sigma_i_data=0,sigma_data=0;
    //             for (uint64_t i2=0;i2<data_shape[2];i2++)
    //             {
    //                 sigma_i_data+=i2*line[i2];
    //                 sigma_data+=line[i2];
    //             }
    //             double sigma_i=(data_shape[2]-1)*data_shape[2]/2;
    //             double sigma_i2=(data_shape[2]-1)*data_shape[2]*(2*data_shape[2]-1)/6;
    //             double a=(data_shape[2]*sigma_i_data-sigma_i*sigma_data)/(data_shape[2]*sigma_i2-sigma_i*sigma_i);
    //             double b=(sigma_i*sigma_i_data-sigma_i2*sigma_data)/(sigma_i*sigma_i-data_shape[2]*sigma_i2);
    //             vector<double> line2(data_shape[2]);
    //             for (uint64_t i2=0;i2<data_shape[2];i2++)
    //                 line2[i2]=line[i2]-a*i2-b;
    //             for (uint64_t lag=0;lag<=10;lag++)
    //             {
    //                 double local_cov=0;
    //                 for (uint64_t i2=lag;i2<data_shape[2];i2++)
    //                     local_cov+=line2[i2]*line2[i2-lag];
    //                 cov[lag]+=local_cov;
    //             }
    //         }
    //     for (uint64_t lag=0;lag<=10;lag++)
    //         cov[lag]/=(data_shape[0]*data_shape[1]*(data_shape[2]-lag));
    //     for (uint64_t lag=1;lag<=10;lag++)
    //     {
    //         cov[lag]/=cov[0];
    //         // printf("lag=%lu, cov=%f, l=%f\n",lag,cov[lag],lag/(-log(cov[lag])));
    //         printf("lag=%lu, cov=%f\n",lag,cov[lag]);
    //     }
    // }
}