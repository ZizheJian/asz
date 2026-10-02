#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::get_default_slope()
    {
        auto start_time=chrono::high_resolution_clock::now();

        vector<T> temp_abs_eb_vec={abs_eb*default_slope_eb_span,abs_eb/default_slope_eb_span};
        T stat_eb=abs_eb*stat_eb_ratio*0.5f;
        T neg_2_stat_eb=1/(2*stat_eb);
        vector<T> average_h1(temp_abs_eb_vec.size()),average_psnr(temp_abs_eb_vec.size());
        vector<size_t> valid_case_num(temp_abs_eb_vec.size());
        for (size_t direction=0;direction<3;direction++)
        {
            vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{0,data_shape[1]},{0,data_shape[2]}};
            block_loc[direction]={3,data_shape[direction]-3};
            vector<uint64_t> stride={1,1,1};
            stride[direction]=2;
            uint64_t dist=1;
            for (size_t i=direction+1;i<3;i++)
                dist*=data_shape[i];
            unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
            get_AB_map(AB_map,data,block_loc,stride,dist,neg_2_stat_eb);
            if (AB_map.empty())
                throw runtime_error("In get_default_slope, direction "+to_string(direction)+" AB_map is empty");
            for (size_t i=0;i<temp_abs_eb_vec.size();i++)
            for (auto t:candidate_t)
            {
                T h1,psnr;
                get_h1_psnr(h1,psnr,AB_map,t,temp_abs_eb_vec[i],stat_eb);
                if (psnr==INFINITY)
                    continue;
                average_h1[i]+=h1;
                average_psnr[i]+=psnr;
                valid_case_num[i]++;
            }
        }
        bool use_fallback=false;
        string fallback_reason="none";
        T max_invalid_ratio=0;
        size_t total_case_num=3*candidate_t.size();
        for (size_t i=0;i<temp_abs_eb_vec.size();i++)
        {
            T invalid_ratio=1-(T)valid_case_num[i]/total_case_num;
            max_invalid_ratio=max(max_invalid_ratio,invalid_ratio);
            if (valid_case_num[i]!=total_case_num)
                printf("Warning: for rel_eb %f, only %zu/%zu valid default-slope cases were found\n",
                    temp_abs_eb_vec[i]/(max_val-min_val),valid_case_num[i],total_case_num);
        }
        if (max_invalid_ratio>=default_slope_invalid_ratio_threshold)
        {
            default_slope=default_slope_fallback;
            use_fallback=true;
            fallback_reason="invalid_ratio";
        }
        else
            for (size_t i=0;i<temp_abs_eb_vec.size();i++)
            {
                average_h1[i]/=valid_case_num[i];
                average_psnr[i]/=valid_case_num[i];
            }
        if (!use_fallback)
        {
            T h1_difference=average_h1[temp_abs_eb_vec.size()-1]-average_h1[0];
            T psnr_difference=average_psnr[temp_abs_eb_vec.size()-1]-average_psnr[0];
            T h1_scale=max((T)1,max(abs(average_h1[temp_abs_eb_vec.size()-1]),abs(average_h1[0])));
            T h1_tolerance=numeric_limits<T>::epsilon()*h1_scale*64;
            if (h1_difference<=h1_tolerance||psnr_difference<=0)
            {
                default_slope=default_slope_fallback;
                use_fallback=true;
                fallback_reason="invalid_difference";
            }
            else
                default_slope=psnr_difference/h1_difference;
        }
        printf("Default slope statistics: max_invalid_ratio=%.6f, fallback=%s, reason=%s, slope=%.6f\n",max_invalid_ratio,use_fallback?"true":"false",fallback_reason.c_str(),default_slope);
        
        auto end_time=chrono::high_resolution_clock::now();
        printf("Get default slope time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    }
}
