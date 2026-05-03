#pragma once

#include <cstdint>
#include <tuple>
#include <functional>
#include <vector>
#include <algorithm>
#include <cmath>
#include <string>
#include <fstream>
#include <iostream>
#include <unordered_map>
#include <random>

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
}

namespace asz
{
    class param_c
    {
        public:
            string original_data_path,compressed_data_path,decompressed_data_path;
            vector<uint64_t> data_shape;
            float min_val,max_val;
            float rel_eb;
            float abs_eb;
            vector<float> data;
            vector<float> compressed_data;
            vector<int64_t> qb_vec;
            vector<int64_t> t_int_vec;

            vector<string> candidate_predictors={"cubic0_120","cubic0_021","cubic0_012","cubic1_120","cubic1_021","cubic1_012","cubic2_120","cubic2_021","cubic2_012"};
            int t_precision=256;//必须大于等于32
            uint64_t h1_block_sampling_num=4096;
            float stat_eb_ratio=0.01;

            vector<float> candidate_t;
            float default_slope;

            bool config_generated=false;
            //////// 可调整参数 ////////
            float pivot_eb_ratio;//pivoting point的误差比例
            float eb_ratio;//所有block共用的相邻layer之间的误差比例
            vector<string> predictor_vec;//预测器列表
            uint64_t block_pivot_ratio;//block边长和pivot间距的比值
            

            vector<uint64_t> block_shape;//block的形状
            vector<uint64_t> pivot_stride;//pivoting point在每个维度上的stride
            vector<uint64_t> block_num;//block在每个维度上的数量

            param_c()
            {
                // 8/32=0.25, 10/32=0.3125
                for (int t_i=6*t_precision/32;t_i<=12*t_precision/32;t_i++)
                    candidate_t.push_back((float)t_i/t_precision);
            }

            void copy_from(param_c &other)
            {
                original_data_path=other.original_data_path;
                compressed_data_path=other.compressed_data_path;
                decompressed_data_path=other.decompressed_data_path;
                data_shape=other.data_shape;
                min_val=other.min_val;
                max_val=other.max_val;
                rel_eb=other.rel_eb;
                abs_eb=other.abs_eb;
                data=other.data;
                compressed_data=other.compressed_data;
                qb_vec=other.qb_vec;
                t_int_vec=other.t_int_vec;
                candidate_predictors=other.candidate_predictors;
                t_precision=other.t_precision;
                h1_block_sampling_num=other.h1_block_sampling_num;
                stat_eb_ratio=other.stat_eb_ratio;
                candidate_t=other.candidate_t;
                default_slope=other.default_slope;
                config_generated=other.config_generated;
                pivot_eb_ratio=other.pivot_eb_ratio;
                eb_ratio=other.eb_ratio;
                predictor_vec=other.predictor_vec;
                block_pivot_ratio=other.block_pivot_ratio;
                block_shape=other.block_shape;
                pivot_stride=other.pivot_stride;
                block_num=other.block_num;
            }

            void get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
                uint64_t dist,float neg_2_stat_eb);
            void get_AB_map_random(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
                uint64_t dist,float neg_2_stat_eb,float max_random_err);
            void get_h1_psnr(float &h1,float &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,float t,float abs_eb,float stat_eb);
            void get_default_slope();
            void print_config();
            void generate_pivot_stride_and_block_shape_and_block_num();
            void generate_config_enumerate();
            void generate_config();
            void generate_config2(float &ret_t,float &ret_h1,float &ret_psnr,string &predictor,vector<uint64_t> &stride,float abs_eb,float stat_eb,float neg_2_stat_eb);
            float compress();
            void block_compress_cubic0_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic0_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic0_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic1_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic1_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic1_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic2_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic2_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic2_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void dot_compress(vector<int64_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,float t,float eb,float neg_2_eb);
    };
}

#include "huffman.hpp"
#include "../third_party/zstd/lib/zstd.h"
#include "get_AB_map.tpp"
#include "get_h_psnr.tpp"
#include "get_default_slope.tpp"
#include "generate_config.tpp"
#include "compress.tpp"
