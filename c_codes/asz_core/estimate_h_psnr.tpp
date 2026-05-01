#pragma once

namespace asz
{
    void param_c::estimate_h1_psnr(float &h1,float &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,float t2,float abs_eb,float stat_eb,uint64_t data_num)
    {
        float neg_2_eb=1/(2*abs_eb);
        unordered_map<int64_t,uint64_t> qb_map;
        float mse=0;
        for (const auto& [AB_key,count]:AB_map)
        {
            float A=get<0>(AB_key)*stat_eb*2;
            float B=get<1>(AB_key)*stat_eb*2;
            float err=A*t2+B;
            int64_t qb=llround(err*neg_2_eb);
            qb_map[qb]+=count;
            float decmp_err=err-qb*abs_eb*2;
            mse+=pow(decmp_err,2)*count;
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

    void param_c::estimate_h2(float &h2,unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> &A2B2_map,float t,float abs_eb,float stat_eb,uint64_t data_num)
    {
        float neg_2_eb=1/(2*abs_eb);
        unordered_map<tuple<int64_t,int64_t>,uint64_t> joint_qb_map;
        unordered_map<int64_t,uint64_t> qb_map;
        float mse=0;
        for (const auto& [A2B2_key,count]:A2B2_map)
        {
            float A1=get<0>(A2B2_key)*stat_eb*2;
            float B1=get<1>(A2B2_key)*stat_eb*2;
            float A2=get<2>(A2B2_key)*stat_eb*2;
            float B2=get<3>(A2B2_key)*stat_eb*2;
            float err1=A1*t+B1;
            float err2=A2*t+B2;
            int64_t qb1=llround(err1*neg_2_eb);
            int64_t qb2=llround(err2*neg_2_eb);
            qb_map[qb1]+=count;
            joint_qb_map[{qb1,qb2}]+=count;
        }
        h2=0;
        for (auto &[joint_qb,freq]:joint_qb_map)
        {
            float joint_p=(float)freq/data_num;
            float cond_p=(float)freq/(qb_map[get<0>(joint_qb)]);
            h2-=joint_p*log2(cond_p);
        }
    }
}