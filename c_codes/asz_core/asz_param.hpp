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
    inline constexpr double one_d_six_quintic_a=3.0/256;
    inline constexpr double one_d_six_quintic_b=-25.0/256;
    inline constexpr double one_d_six_quintic_inner=0.5-one_d_six_quintic_a-one_d_six_quintic_b;

    struct layer_diagnostics_c
    {
        bool enabled=false;
        uint64_t current_layer=0;
        vector<long double> prediction_squared_error,prediction_absolute_error,reconstruction_squared_error,reconstruction_absolute_error;
        vector<uint64_t> count;

        void reset(uint64_t layer_num)
        {
            if(!enabled)
                return;
            prediction_squared_error.assign(layer_num,0);
            prediction_absolute_error.assign(layer_num,0);
            reconstruction_squared_error.assign(layer_num,0);
            reconstruction_absolute_error.assign(layer_num,0);
            count.assign(layer_num,0);
        }

        template<typename T>
        void record(T prediction,T reconstruction,T original)
        {
            if(!enabled)
                return;
            long double prediction_error=(long double)prediction-(long double)original;
            long double reconstruction_error=(long double)reconstruction-(long double)original;
            prediction_squared_error[current_layer]+=prediction_error*prediction_error;
            prediction_absolute_error[current_layer]+=abs(prediction_error);
            reconstruction_squared_error[current_layer]+=reconstruction_error*reconstruction_error;
            reconstruction_absolute_error[current_layer]+=abs(reconstruction_error);
            count[current_layer]++;
        }
    };

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
            double data_range_time=0;
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
            string predictor_family_selector="h1";
            uint64_t predictor_family_suffix_layers=6;
            uint64_t predictor_family_sample_blocks=8;
            uint64_t predictor_family_sample_point_limit=32768;
            T predictor_family_sample_fraction_limit=0.02;
            uint64_t predictor_family_coarse_probe_block_pivot_ratio=3;
            uint64_t predictor_family_fine_probe_block_pivot_ratio=4;
            T predictor_family_fine_eb_threshold=1e-4;
            T default_slope_invalid_ratio_threshold=1;
            T default_slope_fallback=1000;
            T default_slope_eb_span=1.5;

            vector<T> candidate_t;
            vector<T> block_candidate_t;
            string t_policy="adaptive";
            string block_t_policy="peaks";
            T insufficient_sample_t=(T)4/16;
            string quintic_fallback_t_policy="block";
            T quintic_fallback_t=(T)4/16;
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
            layer_diagnostics_c layer_diagnostics;
            

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
                block_candidate_t.clear();
                if (block_t_policy!="peaks"&&block_t_policy!="full")
                    throw invalid_argument("block_t_policy must be peaks or full");
                if (policy=="adaptive")
                {
                    int t_min_i=llround(t_min*t_precision);
                    int t_max_i=llround(t_max*t_precision);
                    for (int t_i=t_min_i;t_i<=t_max_i;t_i++)
                        candidate_t.push_back((T)t_i/t_precision);
                    if (block_t_policy=="peaks")
                    {
                        if (t_precision%32||t_min>(T)1/16||t_max<(T)11/32)
                            throw invalid_argument("peaks block_t_policy requires t_precision divisible by 32 and t range covering [1/16,11/32]");
                        block_candidate_t={(T)1/16,(T)1/4,(T)9/32,(T)5/16,(T)11/32};
                    }
                    else
                        block_candidate_t=candidate_t;
                }
                else if (policy=="fixed_4_16")
                    candidate_t.push_back((T)4/16);
                else if (policy=="fixed_5_16")
                    candidate_t.push_back((T)5/16);
                else
                    throw invalid_argument("t_policy must be adaptive, fixed_4_16, or fixed_5_16");
                if (policy!="adaptive")
                    block_candidate_t=candidate_t;
            }

            template<typename BlockLoc,typename Stride>
            void get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,const vector<T> &data,const BlockLoc &block_loc,const Stride &stride,uint64_t dist,T neg_2_stat_eb);
            void get_h1_psnr(T &h1,T &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,T t,T abs_eb,T stat_eb);
            void get_default_slope();
            void print_config();
            void generate_pivot_stride_and_block_shape_and_block_num();
            void generate_config_enumerate();
            void generate_config(string task);
            void select_predictor_family();
            void select_predictor_family_mse();
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
            T select_block_coefficient(const string &predictor,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T layer_eb,T layer_default_slope,bool &used_fallback);
            void print_layer_diagnostics(const vector<uint64_t> &layer_huffman_bytes);
            T compress();
            void block_compress(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,unsigned char direction,unsigned char qb_order);
            template<bool diagnostics>
            void block_compress_impl(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,unsigned char direction,unsigned char qb_order);
            template<bool diagnostics>
            void dot_compress(vector<qb_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,uint64_t qb_pos);
            void decompress();
            void block_decompress(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char direction,unsigned char qb_order);
            void dot_decompress(vector<qb_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,uint64_t qb_index);
    };
}

#include "huffman.hpp"
#include "../../third_party/zstd/lib/zstd.h"
#include "get_AB_map.tpp"
#include "get_h_psnr.tpp"
#include "get_default_slope.tpp"
#include "generate_config.tpp"
#include "predictor_family.tpp"
#include "compress.tpp"
#include "decompress.tpp"
