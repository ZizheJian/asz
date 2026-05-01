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
    struct hash<tuple<int64_t,int64_t,int64_t,int64_t>>
    {
        size_t operator()(const tuple<int64_t,int64_t,int64_t,int64_t> &t) const
        {
            auto[a,b,c,d]=t;
            int64_t h=0;
            hash_combine(h,a);
            hash_combine(h,b);
            hash_combine(h,c);
            hash_combine(h,d);
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
            vector<bool> data_compressed;
            vector<int64_t> qb_vec;
            vector<int64_t> t_int_vec;


            int t_precision=32;//必须大于等于32
            uint64_t h1_block_sampling_num=1024;
            uint64_t h2_block_sampling_num=8192;
            float stat_eb_ratio=0.1;

            vector<float> possible_t_vec;
            float default_h1_slope;
            float default_h2_slope;

            bool config_generated=false;
            //////// 可调整参数 ////////
            vector<uint64_t> block_shape;//block的形状
            vector<uint64_t> pivot_stride;//pivoting point在每个维度上的stride
            float pivot_eb_ratio;//pivoting point的误差比例
            vector<string> predictor_vec;//每个block的预测器列表
            float eb_ratio;//所有block共用的相邻layer之间的误差比例

            vector<uint64_t> block_num;//block在每个维度上的数量

            param_c()
            {
                for (int t_i=7*t_precision/32;t_i<=11*t_precision/32;t_i++)
                    possible_t_vec.push_back((float)t_i/t_precision);
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
                data_compressed=other.data_compressed;
                qb_vec=other.qb_vec;
                t_int_vec=other.t_int_vec;
                t_precision=other.t_precision;
                h1_block_sampling_num=other.h1_block_sampling_num;
                h2_block_sampling_num=other.h2_block_sampling_num;
                stat_eb_ratio=other.stat_eb_ratio;
                possible_t_vec=other.possible_t_vec;
                default_h1_slope=other.default_h1_slope;
                default_h2_slope=other.default_h2_slope;
                config_generated=other.config_generated;
                block_shape=other.block_shape;
                pivot_stride=other.pivot_stride;
                pivot_eb_ratio=other.pivot_eb_ratio;
                predictor_vec=other.predictor_vec;
                eb_ratio=other.eb_ratio;
                block_num=other.block_num;
            }

            void get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
                uint64_t dist,float neg_2_stat_eb);
            void get_AB_map_random(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
                uint64_t dist,float neg_2_stat_eb,float max_random_err);
            void get_A2B2_map(unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> &A2B2_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,
                vector<uint64_t> &stride,uint64_t dist1,uint64_t dist2,float neg_2_stat_eb);
            void estimate_h1_psnr(float &h1,float &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,float t,float abs_eb,float stat_eb,uint64_t num);
            void estimate_h2(float &h2,unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> &A2B2_map,float t,float abs_eb,float stat_eb,uint64_t num);
            bool compare_curves(vector<float> &h1_curve_oppo,vector<float> &psnr_curve_oppo,vector<float> &h1_curve_base,vector<float> &psnr_curve_base);
            void get_default_slope();
            void get_default_slope2(float &ret_t,vector<float> &ret_h1_curve,vector<float> &ret_psnr_curve,string &predictor,vector<float> &temp_abs_eb_vec,float stat_eb,float neg_2_stat_eb);
            void generate_config_enumerate();
            void generate_config();
            void generate_config2(float &ret_t,float &ret_h1,float &ret_psnr,string &predictor,vector<uint64_t> &stride,float abs_eb,float stat_eb,float neg_2_stat_eb);
            float compress();
            void block_compress_cubic1_231(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic1_132(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic1_123(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic2_231(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic2_132(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic2_123(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic3_231(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic3_132(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void block_compress_cubic3_123(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb);
            void dot_compress(vector<int64_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,float t,float eb,float neg_2_eb);
    };
}

#include "huffman.hpp"
#include "../third_party/zstd/lib/zstd.h"
#include "get_AB_map.tpp"
#include "estimate_h_psnr.tpp"
#include "compare_curves.tpp"
#include "get_default_slope.tpp"
#include "generate_config.tpp"
#include "compress.tpp"
