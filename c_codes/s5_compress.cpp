#include "asz_core/asz_param.hpp"

using namespace std;

// void compress_layer(vector<float> &data,vector<float> &compressed_data,uint64_t block_left0,uint64_t block_left1,uint64_t block_left2,uint64_t block_right0,
//     uint64_t block_right1,uint64_t block_right2,uint32_t layer_id,vector<string> &block_predictor_vec,vector<float> &block_eb_ratio_vec,
//     vector<uint64_t> &stride,conf_c &conf,vector<uint64_t> &standard_block_shape)
// {
//     uint32_t layer_num=block_predictor_vec.size();
//     string predictor=block_predictor_vec[layer_id];
//     float layer_eb=conf.abs_eb;
//     for (uint32_t i=layer_id;i<layer_num;i++)
//         layer_eb*=block_eb_ratio_vec[i];
//     float neg_2_layer_eb=1/(2*layer_eb);
//     uint64_t block_compressed_data_num=(block_right0-block_left0)/stride[0]+1;
//     block_compressed_data_num*=(block_right1-block_left1)/stride[1]+1;
//     block_compressed_data_num*=(block_right2-block_left2)/stride[2]+1;
//     if (block_compressed_data_num>conf.small_block_split_size)
//     {
//         vector<uint64_t> new_block_shape(3),new_block_num(3);
//         if (predictor=="cubic1")
//         {
//             throw runtime_error("cubic1 predictor not implemented");
//         }
//         else if (predictor=="cubic2")
//         {
//             throw runtime_error("cubic2 predictor not implemented");
//         }
//         else if (predictor=="cubic3")
//         {
//             new_block_shape[0]=standard_block_shape[0]/2;
//             new_block_shape[1]=standard_block_shape[1]/2;
//             new_block_shape[2]=standard_block_shape[2];
//             new_block_num[0]=(block_right0-block_left0+new_block_shape[0]-1)/new_block_shape[0];
//             new_block_num[1]=(block_right1-block_left1+new_block_shape[1]-1)/new_block_shape[1];
//             new_block_num[2]=(block_right2-block_left2+new_block_shape[2]-1)/new_block_shape[2];
//             for (uint64_t i0=0;i0<new_block_num[0];i0++)
//                 for (uint64_t i1=0;i1<new_block_num[1];i1++)
//                     for (uint64_t i2=0;i2<new_block_num[2];i2++)
//                     {
//                         uint64_t new_block_left0=block_left0+i0*new_block_shape[0];
//                         uint64_t new_block_left1=block_left1+i1*new_block_shape[1];
//                         uint64_t new_block_left2=block_left2+i2*new_block_shape[2];
//                         uint64_t new_block_right0=min(new_block_left0+new_block_shape[0],block_right0);
//                         uint64_t new_block_right1=min(new_block_left1+new_block_shape[1],block_right1);
//                         uint64_t new_block_right2=min(new_block_left2+new_block_shape[2],block_right2);
//                         compress_layer(data,compressed_data,new_block_left0,new_block_left1,new_block_left2,new_block_right0,new_block_right1,new_block_right2,
//                             layer_id,block_predictor_vec,block_eb_ratio_vec,stride,conf,new_block_shape);
//                     }
//         }
//     }
//     else
//     {
//         float stat_eb=layer_eb*0.01;
//         float neg_2_stat_eb=1/(2*stat_eb);
//         unordered_map<tuple<int64_t,int64_t>,int64_t> AB_map;
//         if (predictor=="cubic1")
//         {
//             throw runtime_error("cubic1 predictor not implemented");
//         }
//         else if (predictor=="cubic2")
//         {
//             throw runtime_error("cubic2 predictor not implemented");
//         }
//         else if (predictor=="cubic3")
//         {
//             uint64_t uncompressed_data_num=1;
//             uint64_t sampling_stride=1;
//             bool sampling_possible=true;
//             while (true)
//             {
//                 uncompressed_data_num=(block_right0-block_left0)/(sampling_stride*stride[0])+1;
//                 uncompressed_data_num*=(block_right1-block_left1)/(sampling_stride*stride[1])+1;
//                 uncompressed_data_num*=(block_right2-block_left2)/(sampling_stride*stride[2])-2;
//                 if ((block_right2-block_left2)/(sampling_stride*stride[2])-2<=0)
//                 {
//                     sampling_possible=false;
//                     break;
//                 }
//                 if (uncompressed_data_num<conf.small_block_sampling_num)
//                     break;
//                 sampling_stride*=2;
//             }
//             float best_t2=0.25;
//             if (sampling_possible)
//             {
//                 for (uint64_t i0=block_left0;i0<=block_right0;i0+=stride[0]*sampling_stride)
//                     for (uint64_t i1=block_left1;i1<=block_right1;i1+=stride[1]*sampling_stride)
//                         for (uint64_t i2=block_left2+3*stride[2]*sampling_stride/2;i2+3*stride[2]*sampling_stride/2<=block_right2;i2+=stride[2]*sampling_stride)
//                         {
//                             uint64_t pos=i0*conf.data_shape[1]*conf.data_shape[2]+i1*conf.data_shape[2]+i2;
//                             double A=-data[pos-3]+data[pos-1]+data[pos+1]-data[pos+3];
//                             int64_t A_key=llround(A*neg_2_stat_eb);
//                             double B=0.25*(data[pos-3]+data[pos-1]+data[pos+1]+data[pos+3])-data[pos];
//                             int64_t B_key=llround(B*neg_2_stat_eb);
//                             AB_map[{A_key,B_key}]++;
//                         }
//                 float best_br=0,best_psnr=0;
//                 for (double t2:conf.t2_vec)
//                 {
//                     unordered_map<int64_t,int64_t> qb_map;
//                     double mse=0;
//                     for (const auto& [AB_key,count]:AB_map)
//                     {
//                         double A=get<0>(AB_key)*stat_eb*2;
//                         double B=get<1>(AB_key)*stat_eb*2;
//                         double err=A*t2+B;
//                         int64_t qb=llround(err*neg_2_layer_eb);
//                         qb_map[qb]+=count;
//                         double decmp_err=err-qb*layer_eb*2;
//                         mse+=pow(decmp_err,2)*count;
//                     }
//                     double H1=0;
//                     for (auto &[qb,freq]:qb_map)
//                     {
//                         double p=(double)freq/uncompressed_data_num;
//                         H1-=p*log2(p);
//                     }
//                     mse/=uncompressed_data_num;
//                     double psnr=-10*log10(mse);
//                     if (t2==conf.t2_vec[0])
//                     {
//                         best_t2=t2;
//                         best_br=H1;
//                         best_psnr=psnr;
//                     }
//                     else if (-conf.default_slope*(H1-best_br)+(psnr-best_psnr)>0)
//                     {
//                         best_t2=t2;
//                         best_br=H1;
//                         best_psnr=psnr;
//                     }
//                 }
//             }
//             vector<int64_t> qb_vec;

//             for (uint64_t i0=block_left0;i0<block_right0;i0+=stride[0])
//                 for (uint64_t i1=block_left1;i1<block_right1;i1+=stride[1])
//                     for (uint64_t i2=block_left2+stride[2]/2;i2+stride[2]/2<=block_right2;i2+=stride[2])
//                     {
//                         uint64_t pos=i0*conf.data_shape[1]*conf.data_shape[2]+i1*conf.data_shape[2]+i2;
//                         if (i2<=stride[2]/2)
                        
//                     }
//         }
//     }

// }

// void compress(vector<float> &data,vector<uint64_t> &data_shape,float abs_eb,conf_c &conf)
// {
//     printf("In compress\n");
//     vector<float> compressed_data;
//     compressed_data.resize(data.size());
//     //////// 存储pivot points ////////
//     vector<int64_t> pivot_qb;
//     pivot_qb.reserve(((data_shape[0]+conf.pivot_stride[0]-1)/conf.pivot_stride[0])*
//                      ((data_shape[1]+conf.pivot_stride[1]-1)/conf.pivot_stride[1])*
//                      ((data_shape[2]+conf.pivot_stride[2]-1)/conf.pivot_stride[2]));
//     float pivot_eb=abs_eb*conf.pivot_eb_ratio;
//     float neg_2_pivot_eb=1/(2*pivot_eb);
//     for (uint64_t i0=0;i0<data_shape[0];i0+=conf.pivot_stride[0])
//         for (uint64_t i1=0;i1<data_shape[1];i1+=conf.pivot_stride[1])
//             for (uint64_t i2=0;i2<data_shape[2];i2+=conf.pivot_stride[2])
//             {
//                 uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
//                 uint64_t qb=llround(data[pos]*neg_2_pivot_eb);
//                 pivot_qb.push_back(qb);
//                 compressed_data[pos]=qb*pivot_eb*2;
//             }
//     //////// 依次处理每个大block ////////
//     for (uint64_t big_block_i0=0;big_block_i0<conf.big_block_num[0];big_block_i0++)
//         for (uint64_t big_block_i1=0;big_block_i1<conf.big_block_num[1];big_block_i1++)
//             for (uint64_t big_block_i2=0;big_block_i2<conf.big_block_num[2];big_block_i2++)
//             {
//                 uint64_t big_block_id=big_block_i0*conf.big_block_num[1]*conf.big_block_num[2]+big_block_i1*conf.big_block_num[2]+big_block_i2;
//                 uint64_t big_block_left0=big_block_i0*conf.big_block_shape[0];
//                 uint64_t big_block_left1=big_block_i1*conf.big_block_shape[1];
//                 uint64_t big_block_left2=big_block_i2*conf.big_block_shape[2];
//                 uint64_t big_block_right0=min(big_block_left0+conf.big_block_shape[0],data_shape[0]);
//                 uint64_t big_block_right1=min(big_block_left1+conf.big_block_shape[1],data_shape[1]);
//                 uint64_t big_block_right2=min(big_block_left2+conf.big_block_shape[2],data_shape[2]);
//                 auto big_block_predictor_vec=conf.predictor_vec[big_block_id];
//                 auto big_block_eb_ratio_vec=conf.eb_ratio_vec[big_block_id];
//                 auto stride=conf.pivot_stride;
//                 //////// 逐层压缩 ////////
                
//             }
// }

int main()
{
    auto param=asz::param_c();
    param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    param.data_shape={100,500,500};
    param.rel_eb=1e-5;

    param.data.resize(param.data_shape[0]*param.data_shape[1]*param.data_shape[2]);
    ifstream data_file(param.original_data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);

    //////// 获得基准斜率 ////////
    param.get_default_slope();
    printf("default_slope=%f\n",param.default_slope);

    // conf.big_block_shape={32,32,32};
    // for (int dim=0;dim<3;dim++)
    //     conf.big_block_num.push_back((data_shape[dim]+conf.big_block_shape[dim]-1)/conf.big_block_shape[dim]);
    // conf.pivot_stride={1,1,2};
    // conf.pivot_eb_ratio=0.5;
    // conf.small_block_split_size=1<<15;
    // conf.small_block_sampling_num=1024;
    // conf.predictor_vec={{"cubic3"}};
    // conf.eb_ratio_vec={{1}};
    // conf.default_slope=conf.get_default_slope();
    // while (true)
    // {
    //     compress(data,data_shape,abs_eb,conf);
    //     exit(0);
    // }
}