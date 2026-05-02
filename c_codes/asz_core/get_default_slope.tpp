#pragma once

namespace asz
{
    void param_c::get_default_slope()
    {
        vector<float> temp_abs_eb_vec={abs_eb*2.0f,abs_eb,abs_eb/2.0f};
        float stat_eb=abs_eb*stat_eb_ratio*2.0f;
        float neg_2_stat_eb=1/(2*stat_eb);
        string best_predictor="";
        unordered_map<string,unordered_map<tuple<float,float>,float>> h1,psnr;//每个predictor在不同rel_eb、t时的h1、psnr
        //////// 获取h1和psnr ////////
        for (auto &predictor:candidate_predictors)
        {
            vector<vector<uint64_t>> block_loc;
            vector<uint64_t> stride;
            unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
            if (predictor.compare(0,6,"cubic0")==0)
            {
                block_loc={{3,data_shape[0]-3},{0,data_shape[1]},{0,data_shape[2]}};
                stride={2,1,1};
                get_AB_map(AB_map,data,block_loc,stride,data_shape[1]*data_shape[2],neg_2_stat_eb);
            }
            else if (predictor.compare(0,6,"cubic1")==0)
            {
                block_loc={{3,data_shape[0]-3},{1,data_shape[1]},{0,data_shape[2]}};
                stride={1,2,1};
                get_AB_map(AB_map,data,block_loc,stride,data_shape[2],neg_2_stat_eb);
            }
            else if (predictor.compare(0,6,"cubic2")==0)
            {
                block_loc={{3,data_shape[0]-3},{0,data_shape[1]},{1,data_shape[2]}};
                stride={1,1,2};
                get_AB_map(AB_map,data,block_loc,stride,1,neg_2_stat_eb);
            }
            if (AB_map.empty())
                throw runtime_error("In get_default_slope, predictor "+predictor+" AB_map is empty");
            for (auto temp_abs_eb:temp_abs_eb_vec)
            for (auto t:candidate_t)
                get_h1_psnr(h1[predictor][{temp_abs_eb,t}],psnr[predictor][{temp_abs_eb,t}],AB_map,t,temp_abs_eb,stat_eb);
        }
        //////// 计算所有predictor、所有t的平均斜率 ////////
        // int valid_slope_num=0;
        // double avg_angle=0;
        // float eb_prev=*temp_abs_eb_vec.begin();
        // float eb_next=*(temp_abs_eb_vec.end()-1);
        // for (auto &predictor:candidate_predictors)
        // for (auto t:candidate_t)
        // {
        //     if ((h1[predictor][{eb_prev,t}]>h1[predictor][{eb_next,t}]) || (psnr[predictor][{eb_prev,t}]>psnr[predictor][{eb_next,t}]))
        //         continue;
        //     if (h1[predictor][{eb_prev,t}]==h1[predictor][{eb_next,t}])
        //         if (psnr[predictor][{eb_prev,t}]==psnr[predictor][{eb_next,t}])
        //             continue;
        //         else
        //         {
        //             avg_angle+=M_PI/2;
        //             valid_slope_num++;
        //         }
        //     else
        //     {
        //         double slope=(psnr[predictor][{eb_next,t}]-psnr[predictor][{eb_prev,t}])/(h1[predictor][{eb_next,t}]-h1[predictor][{eb_prev,t}]);
        //         avg_angle+=atan(slope);
        //         valid_slope_num++;
        //     }
        // }
        // if (valid_slope_num==0)
        //     throw runtime_error("valid_slope_num==0");
        // else
        // {
        //     avg_angle/=valid_slope_num;
        //     if (avg_angle==M_PI/2)
        //         throw runtime_error("slope is infinite");
        //     else
        //         default_slope=tan(avg_angle);
        // }
        vector<float> average_h1(temp_abs_eb_vec.size()),average_psnr(temp_abs_eb_vec.size());
        for (int i=0;i<temp_abs_eb_vec.size();i++)
        {
            for (auto &predictor:candidate_predictors)
            for (auto t:candidate_t)
            {
                average_h1[i]+=h1[predictor][{temp_abs_eb_vec[i],t}];
                average_psnr[i]+=psnr[predictor][{temp_abs_eb_vec[i],t}];
            }
            average_h1[i]/=candidate_predictors.size()*candidate_t.size();
            average_psnr[i]/=candidate_predictors.size()*candidate_t.size();
        }
        for (int i=0;i<temp_abs_eb_vec.size();i++)
        {
            printf("average_h1[%d]=%f\n",i,average_h1[i]);
            printf("average_psnr[%d]=%f\n",i,average_psnr[i]);
        }
        default_slope=(average_psnr[temp_abs_eb_vec.size()-1]-average_psnr[0])/(average_h1[temp_abs_eb_vec.size()-1]-average_h1[0]);
    }
}