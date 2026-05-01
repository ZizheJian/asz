#pragma once

namespace asz
{
    // 四个vector都只有3个数，表示两条包含3个点的折线
    // 检验前一条折线是否比后一条折线好
    bool param_c::compare_curves(vector<float> &h_curve_oppo,vector<float> &psnr_curve_oppo,vector<float> &h_curve_base,vector<float> &psnr_curve_base)
    {
        float k_oppo=(psnr_curve_oppo[2]-psnr_curve_oppo[0])/(h_curve_oppo[2]-h_curve_oppo[0]);
        float k_base=(psnr_curve_base[2]-psnr_curve_base[0])/(h_curve_base[2]-h_curve_base[0]);
        float k_avg=(k_oppo*sqrt(1+k_base*k_base)+k_base*sqrt(1+k_oppo*k_oppo))/(sqrt(1+k_oppo*k_oppo)+sqrt(1+k_base*k_base));
        float dist=(-k_avg*(h_curve_oppo[1]-h_curve_base[1])+psnr_curve_oppo[1]-psnr_curve_base[1])/sqrt(1+k_avg*k_avg);
        return dist>0;
    }
}