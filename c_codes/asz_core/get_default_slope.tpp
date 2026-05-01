#pragma once

namespace asz
{
    // 指定stencil pattern，估计H1和PSNR，寻找最好t
    void param_c::get_default_slope2(float &ret_t,vector<float> &ret_h1_curve,vector<float> &ret_psnr_curve,string &predictor,vector<float> &temp_abs_eb_vec,
        float stat_eb,float neg_2_stat_eb)
    {
        unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
        vector<uint64_t> stride;
        vector<vector<uint64_t>> block_loc;
        if (predictor.compare(0,6,"cubic1")==0)
        {
            stride={2,1,1};
            block_loc={{3,data_shape[0]-3},{0,data_shape[1]},{0,data_shape[2]}};
            get_AB_map(AB_map,data,block_loc,stride,data_shape[1]*data_shape[2],neg_2_stat_eb);
        }
        else if (predictor.compare(0,6,"cubic2")==0)
        {
            stride={1,2,1};
            block_loc={{0,data_shape[0]},{3,data_shape[1]-3},{0,data_shape[2]}};
            get_AB_map(AB_map,data,block_loc,stride,data_shape[2],neg_2_stat_eb);
        }
        else if (predictor.compare(0,6,"cubic3")==0)
        {
            stride={1,1,2};
            block_loc={{0,data_shape[0]},{0,data_shape[1]},{3,data_shape[2]-3}};
            get_AB_map(AB_map,data,block_loc,stride,1,neg_2_stat_eb);
        }
        if (AB_map.empty())
        {
            ret_t=0.25;
            ret_h1_curve={0,0,0};
            ret_psnr_curve={0,0,0};
            return;
        }
        uint64_t sampled_data_num=0;
        for (const auto &[AB_key,count]:AB_map)
            sampled_data_num+=count;

        bool any_t_tried=false;
        float best_t;
        vector<float> best_h1_curve(3),best_psnr_curve(3);
        for (float t:possible_t_vec)
        {
            vector<float> h1_curve(3),psnr_curve(3);
            for (auto temp_abs_eb_id=0;temp_abs_eb_id<temp_abs_eb_vec.size();temp_abs_eb_id++)
            {
                float temp_abs_eb=temp_abs_eb_vec[temp_abs_eb_id];
                float neg_2_eb=1/(2*temp_abs_eb);
                estimate_h1_psnr(h1_curve[temp_abs_eb_id],psnr_curve[temp_abs_eb_id],AB_map,t,temp_abs_eb,stat_eb,sampled_data_num);
            }
            if ((!any_t_tried) || (compare_curves(h1_curve,psnr_curve,best_h1_curve,best_psnr_curve)))
            {
                best_h1_curve=h1_curve;
                best_psnr_curve=psnr_curve;
                best_t=t;
                any_t_tried=true;
            }
        }
        ret_t=best_t;
        ret_h1_curve=best_h1_curve;
        ret_psnr_curve=best_psnr_curve;
    }

    void param_c::get_default_slope()
    {
        vector<string> candidate_predictors={"cubic1_231","cubic1_132","cubic1_123","cubic2_231","cubic2_132","cubic2_123","cubic3_231","cubic3_132","cubic3_123"};
        vector<float> temp_abs_eb_vec={abs_eb*10.0f,abs_eb,abs_eb/10.0f};
        float stat_eb=abs_eb*stat_eb_ratio/10;
        float neg_2_stat_eb=1/(2*stat_eb);
        string best_predictor="";
        vector<float> best_h1_curve(3),best_h2_curve(3),best_psnr_curve(3);
        for (auto &predictor:candidate_predictors)
        {
            float t=0;
            vector<float> h1_curve(3),h2_curve(3),psnr_curve(3);
            get_default_slope2(t,h1_curve,psnr_curve,predictor,temp_abs_eb_vec,stat_eb,neg_2_stat_eb);
            unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> A2B2_map;
            vector<uint64_t> stride;
            vector<vector<uint64_t>> block_loc;
            if (predictor.compare(0,6,"cubic1")==0)
            {
                stride={2,1,1};
                if (predictor=="cubic1_231")
                {
                    block_loc={{5,data_shape[0]-3},{0,data_shape[1]},{0,data_shape[2]}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,data_shape[1]*data_shape[2],data_shape[1]*data_shape[2]*2,neg_2_stat_eb);
                }
                else if (predictor=="cubic1_132")
                {
                    block_loc={{3,data_shape[0]-3},{1,data_shape[1]},{0,data_shape[2]}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,data_shape[1]*data_shape[2],data_shape[2],neg_2_stat_eb);
                }
                else if (predictor=="cubic1_123")
                {
                    block_loc={{3,data_shape[0]-3},{0,data_shape[1]},{1,data_shape[2]}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,data_shape[1]*data_shape[2],1,neg_2_stat_eb);
                }
            }
            else if (predictor.compare(0,6,"cubic2")==0)
            {
                stride={1,2,1};
                if (predictor=="cubic2_231")
                {
                    block_loc={{1,data_shape[0]},{3,data_shape[1]-3},{0,data_shape[2]}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,data_shape[2],data_shape[1]*data_shape[2],neg_2_stat_eb);
                }
                else if (predictor=="cubic2_132")
                {
                    block_loc={{0,data_shape[0]},{5,data_shape[1]-3},{0,data_shape[2]}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,data_shape[2],data_shape[2]*2,neg_2_stat_eb);
                }
                else if (predictor=="cubic2_123")
                {
                    block_loc={{0,data_shape[0]},{3,data_shape[1]-3},{1,data_shape[2]}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,data_shape[2],1,neg_2_stat_eb);
                }
            }
            else if (predictor.compare(0,6,"cubic3")==0)
            {
                stride={1,1,2};
                if (predictor=="cubic3_231")
                {
                    block_loc={{1,data_shape[0]},{0,data_shape[1]},{3,data_shape[2]-3}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,1,data_shape[1]*data_shape[2],neg_2_stat_eb);
                }
                else if (predictor=="cubic3_132")
                {
                    block_loc={{0,data_shape[0]},{1,data_shape[1]},{3,data_shape[2]-3}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,1,data_shape[2],neg_2_stat_eb);
                }
                else if (predictor=="cubic3_123")
                {
                    block_loc={{0,data_shape[0]},{0,data_shape[1]},{5,data_shape[2]-3}};
                    get_A2B2_map(A2B2_map,data,block_loc,stride,1,2,neg_2_stat_eb);
                }
            }
            if (A2B2_map.empty())
            {
                printf("在计算默认斜率、使用%s预测器时，A2B2_map为空\n",predictor.c_str());
                continue;
            }
            uint64_t sampled_data_num=0;
            for (const auto &[A2B2_key,count]:A2B2_map)
                sampled_data_num+=count;
            
            for (auto temp_abs_eb_id=0;temp_abs_eb_id<temp_abs_eb_vec.size();++temp_abs_eb_id)
            {
                float temp_abs_eb=temp_abs_eb_vec[temp_abs_eb_id];
                float neg_2_eb=1/(2*temp_abs_eb);
                estimate_h2(h2_curve[temp_abs_eb_id],A2B2_map,t,temp_abs_eb,stat_eb,sampled_data_num);
            }
            printf("predictor=%s, h1_curve=(%f,%f,%f), h2_curve=(%f,%f,%f), psnr_curve=(%f,%f,%f)\n",predictor.c_str(),h1_curve[0],h1_curve[1],h1_curve[2],
                h2_curve[0],h2_curve[1],h2_curve[2],psnr_curve[0],psnr_curve[1],psnr_curve[2]);
            if ((best_predictor=="") || (compare_curves(h2_curve,psnr_curve,best_h2_curve,best_psnr_curve)))
            {
                best_h1_curve=h1_curve;
                best_h2_curve=h2_curve;
                best_psnr_curve=psnr_curve;
                best_predictor=predictor;
            }
        }
        printf("best_predictor=%s\n",best_predictor.c_str());
        default_h1_slope=(best_psnr_curve[2]-best_psnr_curve[0])/(best_h1_curve[2]-best_h1_curve[0]);
        default_h2_slope=(best_psnr_curve[2]-best_psnr_curve[0])/(best_h2_curve[2]-best_h2_curve[0]);
    }
}