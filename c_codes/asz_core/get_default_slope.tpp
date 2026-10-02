#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::get_default_slope()
    {
        auto start_time=chrono::high_resolution_clock::now();

        vector<T> temp_abs_eb_vec={abs_eb*2.0f,abs_eb*0.5f};
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
        bool use_infinite_slope=false;
        for (size_t i=0;i<temp_abs_eb_vec.size();i++)
        {
            if (valid_case_num[i]==0)
            {
                printf("Warning: all default-slope candidates have zero estimated MSE at rel_eb %f; using slope=1e4\n",temp_abs_eb_vec[i]/(max_val-min_val));
                default_slope=1e4;
                use_infinite_slope=true;
                break;
            }
            average_h1[i]/=valid_case_num[i];
            average_psnr[i]/=valid_case_num[i];
            if (valid_case_num[i]!=3*candidate_t.size())
                printf("Warning: for rel_eb %f, only %zu/%zu valid cases are used to calculate average h1 and psnr\n",
                    temp_abs_eb_vec[i]/(max_val-min_val),valid_case_num[i],3*candidate_t.size());
        }
        if (!use_infinite_slope)
        {
            T h1_difference=average_h1[temp_abs_eb_vec.size()-1]-average_h1[0];
            T psnr_difference=average_psnr[temp_abs_eb_vec.size()-1]-average_psnr[0];
            T h1_scale=max((T)1,max(abs(average_h1[temp_abs_eb_vec.size()-1]),abs(average_h1[0])));
            T h1_tolerance=numeric_limits<T>::epsilon()*h1_scale*64;
            if (h1_difference<=h1_tolerance||psnr_difference<=0)
                default_slope=1e4;
            else
            {
                T estimated_slope=psnr_difference/h1_difference;
                default_slope=estimated_slope>1e4?1e4:estimated_slope;
            }
        }
        
        auto end_time=chrono::high_resolution_clock::now();
        printf("Get default slope time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    }
}
