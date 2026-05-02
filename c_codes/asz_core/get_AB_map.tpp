#pragma once

namespace asz
{
    void param_c::get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
        uint64_t dist,float neg_2_stat_eb)
    {
        uint64_t sampling_stride=(block_loc[0][1]-block_loc[0][0])*(block_loc[1][1]-block_loc[1][0])*(block_loc[2][1]-block_loc[2][0]);
        sampling_stride=pow(((float)sampling_stride/(stride[0]*stride[1]*stride[2]*h1_block_sampling_num)),1.0/3);
        if (sampling_stride==0)
            sampling_stride=1;
        for (uint64_t i0=block_loc[0][0];i0<block_loc[0][1];i0+=stride[0]*sampling_stride)
            for (uint64_t i1=block_loc[1][0];i1<block_loc[1][1];i1+=stride[1]*sampling_stride)
                for (uint64_t i2=block_loc[2][0];i2<block_loc[2][1];i2+=stride[2]*sampling_stride)
                {
                    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                    float A=-data[pos-3*dist]+data[pos-dist]+data[pos+dist]-data[pos+3*dist];
                    float B=0.25*(data[pos-3*dist]+data[pos-dist]+data[pos+dist]+data[pos+3*dist])-data[pos];
                    int64_t A_key=llround(A*neg_2_stat_eb);
                    int64_t B_key=llround(B*neg_2_stat_eb);
                    AB_map[{A_key,B_key}]++;
                }
    }

    // void param_c::get_AB_map_random(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<float> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,
    //     uint64_t dist,float neg_2_stat_eb,float max_random_err)
    // {
    //     static thread_local mt19937 gen(random_device{}());
    //     uniform_real_distribution<float> rand_err(-max_random_err,max_random_err);
    //     uint64_t sampling_stride=(block_loc[0][1]-block_loc[0][0])*(block_loc[1][1]-block_loc[1][0])*(block_loc[2][1]-block_loc[2][0]);
    //     sampling_stride=pow(((float)sampling_stride/(stride[0]*stride[1]*stride[2]*h1_block_sampling_num)),1.0/3);
    //     if (sampling_stride==0)
    //         sampling_stride=1;
    //     for (uint64_t i0=block_loc[0][0];i0<block_loc[0][1];i0+=stride[0]*sampling_stride)
    //         for (uint64_t i1=block_loc[1][0];i1<block_loc[1][1];i1+=stride[1]*sampling_stride)
    //             for (uint64_t i2=block_loc[2][0];i2<block_loc[2][1];i2+=stride[2]*sampling_stride)
    //             {
    //                 uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
    //                 float v_l3=data[pos-3*dist]+rand_err(gen);
    //                 float v_l1=data[pos-dist]+rand_err(gen);
    //                 float v_m=data[pos]+rand_err(gen);
    //                 float v_r1=data[pos+dist]+rand_err(gen);
    //                 float v_r3=data[pos+3*dist]+rand_err(gen);
    //                 float A=-v_l3+v_l1+v_r1-v_r3;
    //                 float B=0.25*(v_l3+v_l1+v_r1+v_r3)-v_m;
    //                 int64_t A_key=llround(A*neg_2_stat_eb);
    //                 int64_t B_key=llround(B*neg_2_stat_eb);
    //                 AB_map[{A_key,B_key}]++;
    //             }
    // }
}