#pragma once

#include <cstdint>
#include <tuple>
#include <functional>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <fstream>
#include <iostream>
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
            vector<vector<int64_t>> qb_vec_vec;
            vector<int64_t> t_int_vec;

            vector<string> candidate_predictors={"cubic0_120","cubic0_021","cubic0_012","cubic1_120","cubic1_021","cubic1_012","cubic2_120","cubic2_021","cubic2_012"};
            int t_precision=16;//必须大于等于32
            uint64_t h1_block_sampling_num=256;
            T stat_eb_ratio=0.1;
            uint64_t generate_config_sample_stride=8;

            vector<T> candidate_t;
            T default_slope;

            bool config_generated=false;
            //////// 可调整参数 ////////
            T pivot_eb_ratio=0.10;//pivoting point的误差比例
            T eb_ratio=0.72;//相邻layer之间的误差比例
            T slope_ratio=0.54;//相邻layer之间的斜率比例
            vector<string> predictor_vec;//预测器列表
            uint64_t block_pivot_ratio=4;//block边长和pivot间距的比值
            bool force_quintic=false;//整个dataset统一使用quintic内部预测
            bool auto_select_predictor_family=true;
            

            vector<uint64_t> block_shape;//block的形状
            vector<uint64_t> pivot_stride;//pivoting point在每个维度上的stride
            vector<uint64_t> block_num;//block在每个维度上的数量

            param_c()
            {
                // 8/32=0.25, 10/32=0.3125
                for (int t_i=6*t_precision/32;t_i<=12*t_precision/32;t_i++)
                    candidate_t.push_back((T)t_i/t_precision);
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
                h1_block_sampling_num=other.h1_block_sampling_num;
                stat_eb_ratio=other.stat_eb_ratio;
                generate_config_sample_stride=other.generate_config_sample_stride;
                candidate_t.assign(other.candidate_t.begin(),other.candidate_t.end());
                default_slope=other.default_slope;
                config_generated=other.config_generated;
                pivot_eb_ratio=other.pivot_eb_ratio;
                eb_ratio=other.eb_ratio;
                slope_ratio=other.slope_ratio;
                predictor_vec=other.predictor_vec;
                block_pivot_ratio=other.block_pivot_ratio;
                force_quintic=other.force_quintic;
                auto_select_predictor_family=other.auto_select_predictor_family;
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
            void block_sample_compress_cubic0_120(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic0_021(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic0_012(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic1_120(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic1_021(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic1_012(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic2_120(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void block_sample_compress_cubic2_021(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_sample_compress_cubic2_012(vector<int64_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
                vector<uint64_t> &stride,T t,T eb,T neg_2_ebtemp_stride);
            void dot_sample_compress(vector<int64_t> &qb_vec,T &mse,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,
                T neg_2_eb);
            T compress();
            void block_compress_cubic0_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic0_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic0_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic1_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic1_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic1_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic2_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic2_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void block_compress_cubic2_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb);
            void dot_compress(vector<int64_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,T neg_2_eb);
            void decompress();
            void block_decompress_cubic0_120(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic0_021(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic0_012(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic1_120(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic1_021(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic1_012(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic2_120(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic2_021(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void block_decompress_cubic2_012(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb);
            void dot_decompress(vector<int64_t> &qb_vec,uint64_t &qb_pos,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb);
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
