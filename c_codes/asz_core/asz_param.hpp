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
            vector<vector<int64_t>> qb_vec;
            vector<int64_t> t2_int_vec;


            int t2_precision=32;//必须大于等于16
            uint64_t small_block_sampling_num=1024;//每个小block中为了决定t2需要采样的数据量，应该远小于small_block_split_size

            vector<float> possible_t2_vec;
            float default_slope;

            bool config_generated=false;
            //////// 可调整参数 ////////
            vector<uint64_t> block_shape;//block的形状
            vector<uint64_t> pivot_stride;//pivoting point在每个维度上的stride
            float pivot_eb_ratio;//pivoting point的误差比例
            vector<vector<string>> predictor_vec;//每个block的预测器列表
            float eb_ratio;//所有block共用的相邻layer之间的误差比例

            vector<uint64_t> block_num;//block在每个维度上的数量

            param_c()
            {
                for (int t2_i=3*t2_precision/16;t2_i<=6*t2_precision/16;t2_i++)
                    possible_t2_vec.push_back((float)t2_i/t2_precision);
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
                t2_int_vec=other.t2_int_vec;
                t2_precision=other.t2_precision;
                small_block_sampling_num=other.small_block_sampling_num;
                possible_t2_vec=other.possible_t2_vec;
                default_slope=other.default_slope;
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
            void estimate_br_psnr(float &br,float &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,float t2,float abs_eb,float stat_eb,uint64_t num);
            bool compare_curves1(vector<float> &H1_vec,vector<float> &PSNR_vec,vector<float> &H1_vec_base,vector<float> &PSNR_vec_base);
            void get_default_slope();
            void generate_config_enumerate();
            void generate_config();
            float compress();
            void block_compress_cubic1(vector<int64_t> &temp_qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float best_t2,float layer_eb,
                float neg_2_layer_eb);
            void block_compress_cubic2(vector<int64_t> &temp_qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float best_t2,float layer_eb,
                float neg_2_layer_eb);
            void block_compress_cubic3(vector<int64_t> &temp_qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float best_t2,float layer_eb,
                float neg_2_layer_eb);
            void dot_compress(vector<int64_t> &temp_qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,float t2,
                float neg_2_layer_eb,float layer_eb);
    };
}

#include "huffman.hpp"
#include "../third_party/zstd/lib/zstd.h"
#include "get_AB_map.tpp"
#include "estimate_br_psnr.tpp"
#include "compare_curves.tpp"
#include "get_default_slope.tpp"
#include "generate_config.tpp"
#include "compress.tpp"
