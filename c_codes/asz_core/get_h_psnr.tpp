#pragma once

namespace asz
{
    void param_c::get_h1_psnr(float &h1,float &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,float t,float abs_eb,float stat_eb)
    {
        float neg_2_eb=1/(2*abs_eb);
        unordered_map<int64_t,uint64_t> qb_map;
        float mse=0;
        uint64_t data_num=0;
        for (const auto& [AB_key,count]:AB_map)
        {
            float A=get<0>(AB_key)*stat_eb*2;
            float B=get<1>(AB_key)*stat_eb*2;
            float err=A*t+B;
            int64_t qb=llround(err*neg_2_eb);
            qb_map[qb]+=count;
            float decmp_err=err-qb*abs_eb*2;
            mse+=pow(decmp_err,2)*count;
            data_num+=count;
        }
        h1=0;
        for (auto &[qb,freq]:qb_map)
        {
            float p=(float)freq/data_num;
            h1-=p*log2(p);
        }
        mse/=data_num;
        psnr=10*log10((max_val-min_val)*(max_val-min_val)/mse);
    }
}