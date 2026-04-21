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
            vector<float> decompressed_data;
            vector<bool> data_compressed;

            int t2_precision=128;//必须大于等于16
            uint64_t small_block_sampling_num=2048;//每个小block中为了决定t2需要采样的数据量，应该远小于small_block_split_size

            vector<float> t2_vec;
            float default_slope;

            //////// 可调整参数 ////////
            vector<uint64_t> big_block_shape;//大block的形状
            vector<uint64_t> pivot_stride;//pivoting point在每个维度上的stride
            float pivot_eb_ratio;//pivoting point的误差比例
            uint64_t small_block_split_size;//每个小block分裂前的数据量，可以设置的非常大来避免分裂
            vector<vector<string>> predictor_vec;//每个大block的预测器列表
            vector<vector<double>> eb_ratio_vec;//每个大block的误差比例列表

            vector<uint64_t> big_block_num;//大block在每个维度上的数量

            param_c()
            {
                for (int t2_i=7*t2_precision/32;t2_i<=11*t2_precision/32;t2_i++)
                    t2_vec.push_back((float)t2_i/t2_precision);
            }

            void get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
                uint64_t dist,float neg_2_stat_eb);
            void estimate_br_psnr(float &br,float &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,float t2,float abs_eb,float stat_eb,uint64_t num);
            bool compare_curves1(vector<float> &H1_vec,vector<float> &PSNR_vec,vector<float> &H1_vec_base,vector<float> &PSNR_vec_base);
            void get_default_slope();
    };
}

#include "get_AB_map.tpp"
#include "estimate_br_psnr.tpp"
#include "compare_curves.tpp"
#include "get_default_slope.tpp"
