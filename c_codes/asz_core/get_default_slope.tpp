#pragma once

namespace asz
{
    // 尝试3种不同方向的三阶插值
    // 对于每一种插值预测，先选择合适的采样间隔，然后统计A和B的分布，通过微调abs_eb估算出斜率
    // 最后选择性能最好的一种作为默认斜率
    void param_c::get_default_slope()
    {
        vector<string> predictor_vec={"cubic1","cubic2","cubic3"};
        vector<float> temp_abs_eb_vec={abs_eb*1.5f,abs_eb,abs_eb/1.5f};
        float stat_eb=abs_eb/150;
        float neg_2_stat_eb=1/(2*stat_eb);
        bool no_valid_result=true;
        vector<float> best_H1_vec(3),best_PSNR_vec(3);
        string best_predictor;
        float best_t2;
        vector<float> H1_vec(3),PSNR_vec(3);
        for (auto &predictor:predictor_vec)
        {
            unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
            vector<uint64_t> stride;
            vector<vector<uint64_t>> block_loc;
            if (predictor=="cubic1")
            {
                stride={2,1,1};
                block_loc={{3,data_shape[0]-3},{0,data_shape[1]},{0,data_shape[2]}};
                get_AB_map(AB_map,data,block_loc,stride,data_shape[1]*data_shape[2],neg_2_stat_eb);
            }
            else if (predictor=="cubic2")
            {
                stride={1,2,1};
                block_loc={{0,data_shape[0]},{3,data_shape[1]-3},{0,data_shape[2]}};
                get_AB_map(AB_map,data,block_loc,stride,data_shape[2],neg_2_stat_eb);
            }
            else if (predictor=="cubic3")
            {
                stride={1,1,2};
                block_loc={{0,data_shape[0]},{0,data_shape[1]},{3,data_shape[2]-3}};
                get_AB_map(AB_map,data,block_loc,stride,1,neg_2_stat_eb);
            }
            if (AB_map.empty())
            {
                printf("在计算默认斜率、使用%s预测器时，AB_map为空\n", predictor.c_str());
                continue;
            }
            uint64_t compressed_data_num=0;
            for (const auto &[AB_key,count]:AB_map)
                compressed_data_num+=count;
            for (float t2:t2_vec)
            {
                for (auto temp_abs_eb_id=0;temp_abs_eb_id<temp_abs_eb_vec.size();++temp_abs_eb_id)
                {
                    float temp_abs_eb=temp_abs_eb_vec[temp_abs_eb_id];
                    float neg_2_eb=1/(2*temp_abs_eb);
                    estimate_br_psnr(H1_vec[temp_abs_eb_id],PSNR_vec[temp_abs_eb_id],AB_map,t2,temp_abs_eb,stat_eb,compressed_data_num);
                    printf("temp_abs_eb=%e, t2=%f, H1=%f, PSNR=%f\n",temp_abs_eb,t2,H1_vec[temp_abs_eb_id],PSNR_vec[temp_abs_eb_id]);
                }
                if ((no_valid_result) || (compare_curves1(H1_vec,PSNR_vec,best_H1_vec,best_PSNR_vec)))
                {
                    best_H1_vec=H1_vec;
                    best_PSNR_vec=PSNR_vec;
                    best_predictor=predictor;
                    best_t2=t2;
                    no_valid_result=false;
                }
            }
        }
        printf("best_predictor=%s, best_t2=%f\n",best_predictor.c_str(),best_t2);
        default_slope=(best_PSNR_vec[2]-best_PSNR_vec[0])/(best_H1_vec[2]-best_H1_vec[0]);
    }
}