#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::get_h1_psnr(T &h1,T &psnr,unordered_map<tuple<int64_t,int64_t>,uint64_t> &AB_map,T t,T abs_eb,T stat_eb)
    {
        T neg_2_eb=1/(2*abs_eb);
        unordered_map<int64_t,uint64_t> qb_map;
        T mse=0;
        uint64_t data_num=0;
        for (const auto& [AB_key,count]:AB_map)
        {
            T A=get<0>(AB_key)*stat_eb*2;
            T B=get<1>(AB_key)*stat_eb*2;
            T err=A*t+B;
            int64_t qb=llround(err*neg_2_eb);
            qb_map[qb]+=count;
            T decmp_err=err-qb*abs_eb*2;
            mse+=pow(decmp_err,2)*count;
            data_num+=count;
        }
        h1=0;
        for (auto &[qb,freq]:qb_map)
        {
            T p=(T)freq/data_num;
            h1-=p*log2(p);
        }
        mse/=data_num;
        psnr=10*log10((max_val-min_val)*(max_val-min_val)/mse);
    }
}