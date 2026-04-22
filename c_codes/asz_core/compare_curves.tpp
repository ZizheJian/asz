#pragma once

namespace asz
{
    // 四个vector都只有3个数，表示两条包含3个点的折线
    // 检验前一条折线是否比后一条折线好
    bool param_c::compare_curves1(vector<float> &H1_vec,vector<float> &PSNR_vec,vector<float> &H1_vec_base,vector<float> &PSNR_vec_base)
    {
        float k=(PSNR_vec[2]-PSNR_vec[0])/(H1_vec[2]-H1_vec[0]);
        float k_base=(PSNR_vec_base[2]-PSNR_vec_base[0])/(H1_vec_base[2]-H1_vec_base[0]);
        float k_avg=(k*sqrt(1+k_base*k_base)+k_base*sqrt(1+k*k))/(sqrt(1+k*k)+sqrt(1+k_base*k_base));
        // printf("k=%f, k_base=%f, k_avg=%f\n", k, k_base, k_avg);
        float dist=(-k_avg*(H1_vec[1]-H1_vec_base[1])+PSNR_vec[1]-PSNR_vec_base[1])/sqrt(1+k_avg*k_avg);
        // printf("dist=%f\n", dist);
        return dist>0;
    }
}