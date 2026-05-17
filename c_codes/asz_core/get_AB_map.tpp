#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::get_AB_map(unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,vector<T> &data,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,uint64_t dist,
        T neg_2_stat_eb)
    {
        uint64_t sampling_stride=(block_loc[0][1]-block_loc[0][0])*(block_loc[1][1]-block_loc[1][0])*(block_loc[2][1]-block_loc[2][0]);
        sampling_stride=pow(((T)sampling_stride/(stride[0]*stride[1]*stride[2]*h1_block_sampling_num)),1.0/3);
        if (sampling_stride==0)
            sampling_stride=1;
        for (uint64_t i0=block_loc[0][0];i0<block_loc[0][1];i0+=stride[0]*sampling_stride)
            for (uint64_t i1=block_loc[1][0];i1<block_loc[1][1];i1+=stride[1]*sampling_stride)
                for (uint64_t i2=block_loc[2][0];i2<block_loc[2][1];i2+=stride[2]*sampling_stride)
                {
                    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                    T A=-data[pos-3*dist]+data[pos-dist]+data[pos+dist]-data[pos+3*dist];
                    T B=0.25*(data[pos-3*dist]+data[pos-dist]+data[pos+dist]+data[pos+3*dist])-data[pos];
                    int64_t A_key=llround(A*neg_2_stat_eb);
                    int64_t B_key=llround(B*neg_2_stat_eb);
                    AB_map[{A_key,B_key}]++;
                }
    }
}