#pragma once

#include <cstdint>
#include <array>
#include <tuple>
#include <functional>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <unordered_map>
#include <random>
#include <chrono>

using namespace std;

inline void hash_combine(int64_t &v1,int64_t v2)
{
    v1=v1*1145141919810+v2;
}

namespace std
{
    template<>
    struct hash<tuple<int64_t,int64_t>>
    {
        size_t operator()(const tuple<int64_t,int64_t> &t) const
        {
            auto[a,b]=t;
            int64_t h=0;
            hash_combine(h,a);
            hash_combine(h,b);
            return h;
        }
    };

    template<>
    struct hash<tuple<float,float>>
    {
        size_t operator()(const tuple<float,float> &t) const
        {
            auto[a,b]=t;
            int64_t h=0;
            hash_combine(h,hash<double>{}(a));
            hash_combine(h,hash<double>{}(b));
            return h;
        }
    };

    template<>
    struct hash<tuple<double,double>>
    {
        size_t operator()(const tuple<double,double> &t) const
        {
            auto[a,b]=t;
            int64_t h=0;
            hash_combine(h,hash<double>{}(a));
            hash_combine(h,hash<double>{}(b));
            return h;
        }
    };
}

namespace asz
{
    using qb_t=int32_t;

    template<typename BlockLoc,typename Stride>
    inline array<uint64_t,3> get_layer_qb_shape(const BlockLoc &block_loc,const Stride &stride,unsigned char direction)
    {
        array<uint64_t,3> qb_shape;
        for (uint64_t dim=0;dim<3;dim++)
        {
            uint64_t start=dim==direction?block_loc[dim][0]+stride[dim]/2:(block_loc[dim][0]==0?0:block_loc[dim][0]+stride[dim]);
            qb_shape[dim]=start>=block_loc[dim][1]?0:(block_loc[dim][1]-start+stride[dim]-1)/stride[dim];
        }
        return qb_shape;
    }

    inline uint64_t get_layer_qb_num(const array<uint64_t,3> &qb_shape)
    {
        return qb_shape[0]*qb_shape[1]*qb_shape[2];
    }

    inline uint64_t get_qb_index(uint64_t i0,uint64_t i1,uint64_t i2,const array<uint64_t,3> &qb_shape,unsigned char order)
    {
        if (order==0)
            return (i1*qb_shape[2]+i2)*qb_shape[0]+i0;
        if (order==1)
            return (i0*qb_shape[2]+i2)*qb_shape[1]+i1;
        return (i0*qb_shape[1]+i1)*qb_shape[2]+i2;
    }

    template<typename T>
    class param_c
    {
        public:
            string original_data_path,compressed_data_path,decompressed_data_path;
            vector<uint64_t> data_shape;
            T min_val,max_val;
            T rel_eb;
            T abs_eb;
            vector<T> data;
            vector<unsigned char> zstd_bs_vec;
            vector<T> compressed_data;
            vector<vector<qb_t>> qb_vec_vec;
            vector<int64_t> t_int_vec;

            vector<string> candidate_predictors={"cubic0_120","cubic0_021","cubic0_012","cubic1_120","cubic1_021","cubic1_012","cubic2_120","cubic2_021","cubic2_012"};
            int t_precision=32;
            T t_min=(T)1/16;
            T t_max=(T)6/16;
            uint64_t h1_block_sampling_num=256;
            T stat_eb_ratio=0.2;
            uint64_t generate_config_sample_stride=5;
            uint64_t predictor_family_sample_limit=10000;
            T predictor_family_mse_ratio_threshold=0.97;
            T default_slope_invalid_ratio_threshold=1;
            T default_slope_fallback=1000;
            T default_slope_eb_span=1.5;

            vector<T> candidate_t;
            string t_policy="adaptive";
            T default_slope;

            bool config_generated=false;
            //////// 可调整参数 ////////
            T pivot_eb_ratio=0.05;//pivoting point的误差比例
            T eb_ratio=0.76;//相邻layer之间的误差比例
            T slope_ratio=0.54;//相邻layer之间的斜率比例
            uint64_t max_layer_num=14;//自动生成plan时允许的最大层数
            uint64_t full_predictor_search_layer_num=4;//前几轮生成层搜索全部遍历顺序
            vector<string> predictor_vec;//预测器列表
            uint64_t block_pivot_ratio=4;//block边长和pivot间距的比值
            bool force_quintic=false;//整个dataset统一使用quintic内部预测
            bool auto_select_predictor_family=true;
            bool report_t_histogram=false;
            

            vector<uint64_t> block_shape;//block的形状
            vector<uint64_t> pivot_stride;//pivoting point在每个维度上的stride
            vector<uint64_t> block_num;//block在每个维度上的数量

            param_c()
            {
                set_t_policy("adaptive");
            }

            void set_t_policy(const string &policy)
            {
                t_policy=policy;
                candidate_t.clear();
                if (policy=="adaptive")
                {
                    int t_min_i=llround(t_min*t_precision);
                    int t_max_i=llround(t_max*t_precision);
                    for (int t_i=t_min_i;t_i<=t_max_i;t_i++)
                        candidate_t.push_back((T)t_i/t_precision);
                }
                else if (policy=="fixed_4_16")
                    candidate_t.push_back((T)4/16);
                else if (policy=="fixed_5_16")
                    candidate_t.push_back((T)5/16);
                else
                    throw invalid_argument("t_policy must be adaptive, fixed_4_16, or fixed_5_16");
            }

            template<typename T2>
            void copy_from(param_c<T2> &other)
            {
                original_data_path=other.original_data_path;
                compressed_data_path=other.compressed_data_path;
                decompressed_data_path=other.decompressed_data_path;
                data_shape=other.data_shape;
                min_val=other.min_val;
                max_val=other.max_val;
                rel_eb=other.rel_eb;
                abs_eb=other.abs_eb;
                data.assign(other.data.begin(),other.data.end());
                zstd_bs_vec=other.zstd_bs_vec;
                compressed_data.assign(other.compressed_data.begin(),other.compressed_data.end());
                qb_vec_vec=other.qb_vec_vec;
                t_int_vec=other.t_int_vec;
                candidate_predictors=other.candidate_predictors;
                t_precision=other.t_precision;
                t_min=other.t_min;
                t_max=other.t_max;
                h1_block_sampling_num=other.h1_block_sampling_num;
                stat_eb_ratio=other.stat_eb_ratio;
                generate_config_sample_stride=other.generate_config_sample_stride;
                predictor_family_sample_limit=other.predictor_family_sample_limit;
                predictor_family_mse_ratio_threshold=other.predictor_family_mse_ratio_threshold;
                default_slope_invalid_ratio_threshold=other.default_slope_invalid_ratio_threshold;
                default_slope_fallback=other.default_slope_fallback;
                default_slope_eb_span=other.default_slope_eb_span;
                candidate_t.assign(other.candidate_t.begin(),other.candidate_t.end());
                t_policy=other.t_policy;
                default_slope=other.default_slope;
                config_generated=other.config_generated;
                pivot_eb_ratio=other.pivot_eb_ratio;
                eb_ratio=other.eb_ratio;
                slope_ratio=other.slope_ratio;
                max_layer_num=other.max_layer_num;
                full_predictor_search_layer_num=other.full_predictor_search_layer_num;
                predictor_vec=other.predictor_vec;
                block_pivot_ratio=other.block_pivot_ratio;
                force_quintic=other.force_quintic;
                auto_select_predictor_family=other.auto_select_predictor_family;
                report_t_histogram=other.report_t_histogram;
                block_shape=other.block_shape;
                pivot_stride=other.pivot_stride;
                block_num=other.block_num;
            }

            void get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<T> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
                uint64_t dist,T neg_2_stat_eb);
            void get_h1_psnr(T &h1,T &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,T t,T abs_eb,T stat_eb);
            void get_default_slope();
            void print_config();
            void generate_pivot_stride_and_block_shape_and_block_num();
            void generate_config_enumerate();
            void generate_config(string task);
            void select_predictor_family();
            void block_sample_compress_cubic0_120(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic0_021(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic0_012(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic1_120(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic1_021(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic1_012(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic2_120(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic2_021(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_sample_compress_cubic2_012(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void dot_sample_compress(vector<qb_t> &qb_vec,T &mse,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,
                T neg_2_eb);
            T compress();
            void block_compress_cubic0_120(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic0_021(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic0_012(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb,unsigned char qb_order=2);
            void block_compress_cubic1_120(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic1_021(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic1_012(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb,unsigned char qb_order=2);
            void block_compress_cubic2_120(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic2_021(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic2_012(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb,unsigned char qb_order=2);
            void dot_compress(vector<qb_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,T neg_2_eb,uint64_t qb_pos=numeric_limits<uint64_t>::max());
            void decompress();
            void block_decompress_cubic0_120(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb);
            void block_decompress_cubic0_021(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb);
            void block_decompress_cubic0_012(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char qb_order=2);
            void block_decompress_cubic1_120(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb);
            void block_decompress_cubic1_021(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb);
            void block_decompress_cubic1_012(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char qb_order=2);
            void block_decompress_cubic2_120(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb);
            void block_decompress_cubic2_021(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb);
            void block_decompress_cubic2_012(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char qb_order=2);
            void dot_decompress(vector<qb_t> &qb_vec,uint64_t &qb_pos,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,uint64_t qb_index=numeric_limits<uint64_t>::max());
    };
}

#include "huffman.hpp"
#include "../../third_party/zstd/lib/zstd.h"
#include "get_AB_map.tpp"
#include "get_h_psnr.tpp"
#include "get_default_slope.tpp"
#include "generate_config.tpp"
#include "compress.tpp"
#include "decompress.tpp"
