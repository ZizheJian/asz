#pragma once

namespace asz
{
    void param_c::generate_config_enumerate()
    {
        //////// 用于搜索一个合适的config ////////
        if (!config_generated)
        {
            //////// 这里写初始配置 ////////
            block_shape={32,64,64};
            pivot_stride={8,16,16};
            pivot_eb_ratio=0.204343;
            eb_ratio=0.960596;
            
            for (int dim=0;dim<3;dim++)
                block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
            predictor_vec={"cubic3_231","cubic2_231","cubic1_132","cubic2_123","cubic1_123","cubic3_123","cubic3_123","cubic2_123","cubic1_123","cubic2_123","cubic3_132"};

            config_generated=true;
            printf("pivot_eb_ratio=%f\n",pivot_eb_ratio);
            printf("eb_ratio=%f\n",eb_ratio);
            for (auto predictor:predictor_vec)
                printf("\"%s\",",predictor.c_str());
            printf("\n");
            
        }
        else
        {
            //////// 这里写搜索策略 ////////
            int step=(uint64_t)log2(pivot_stride[0])+(uint64_t)log2(pivot_stride[1])+(uint64_t)log2(pivot_stride[2]);
            while (true)
            {
                int change_pos=rand()%(step+2);
                if (change_pos==0)
                {
                    //////// 改变pivot_eb_ratio ////////
                    int power=round(log(pivot_eb_ratio)/log(0.99));
                    if ((power==0) || (rand()%2==1))
                        power++;
                    else
                        power--;
                    pivot_eb_ratio=pow(0.99,power);
                    break;
                }
                else if (1<=change_pos && change_pos<=step)
                {
                    //////// 更改predictor_vec ////////
                    int idx=change_pos-1;
                    string old_predictor=predictor_vec[idx];
                    vector<string> candidate_predictors={"cubic1_231","cubic1_132","cubic1_123","cubic2_231","cubic2_132","cubic2_123","cubic3_231","cubic3_132","cubic3_123"};
                    string new_perdictor=old_predictor;
                    while (new_perdictor==old_predictor)
                        new_perdictor=candidate_predictors[rand()%candidate_predictors.size()];
                    predictor_vec[idx]=new_perdictor;
                    if (old_predictor.compare(0,6,"cubic1")==0)
                        pivot_stride[0]/=2;
                    else if (old_predictor.compare(0,6,"cubic2")==0)
                        pivot_stride[1]/=2;
                    else if (old_predictor.compare(0,6,"cubic3")==0)
                        pivot_stride[2]/=2;
                    if (new_perdictor.compare(0,6,"cubic1")==0)
                        pivot_stride[0]*=2;
                    else if (new_perdictor.compare(0,6,"cubic2")==0)
                        pivot_stride[1]*=2;
                    else if (new_perdictor.compare(0,6,"cubic3")==0)
                        pivot_stride[2]*=2;
                    break;
                    block_shape={pivot_stride[0]*4,pivot_stride[1]*4,pivot_stride[2]*4};
                    block_num.clear();
                    for (int dim=0;dim<3;dim++)
                        block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
                }
                else
                {
                    //////// 改变eb_ratio ////////
                    int power=round(log(eb_ratio)/log(0.99));
                    if ((power==0) || (rand()%2==1))
                        power++;
                    else
                        power--;
                    eb_ratio=pow(0.99,power);
                    break;
                }
            }
            printf("pivot_eb_ratio=%f\n",pivot_eb_ratio);
            printf("eb_ratio=%f\n",eb_ratio);
            for (auto predictor:predictor_vec)
                printf("\"%s\",",predictor.c_str());
            printf("\n");
        }
    }

    void param_c::generate_config2(float &ret_t,float &ret_h1,float &ret_psnr,string &predictor,vector<uint64_t> &stride,float abs_eb,float stat_eb,float neg_2_stat_eb)
    {
        // 由generate_config调用，用于找到一个stencil pattern最好的t
        unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
        vector<vector<uint64_t>> block_loc;
        if ((predictor.compare(0,6,"cubic1")==0) && (data_shape[0]>6*stride[0]))
        {
            stride[0]*=2;
            block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
            get_AB_map(AB_map,data,block_loc,stride,data_shape[1]*data_shape[2],neg_2_stat_eb);
            stride[0]/=2;
        }
        else if ((predictor.compare(0,6,"cubic2")==0) && (data_shape[1]>6*stride[1]))
        {
            stride[1]*=2;
            block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
            get_AB_map(AB_map,data,block_loc,stride,data_shape[2],neg_2_stat_eb);
            stride[1]/=2;
        }
        else if ((predictor.compare(0,6,"cubic3")==0) && (data_shape[2]>6*stride[2]))
        {
            stride[2]*=2;
            block_loc={{0,data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
            get_AB_map(AB_map,data,block_loc,stride,1,neg_2_stat_eb);
            stride[2]/=2;
        }
        if (AB_map.empty())
        {
            ret_t=0.25;
            return;
        }
        uint64_t sampled_data_num=0;
        for (const auto &[AB_key,count]:AB_map)
            sampled_data_num+=count;

        bool any_t_tried=false;
        float best_t,best_h1,best_psnr;
        for (float t:possible_t_vec)
        {
            float h1,psnr;
            float neg_2_eb=1/(2*abs_eb);
            estimate_h1_psnr(h1,psnr,AB_map,t,abs_eb,stat_eb,sampled_data_num);
            if ((!any_t_tried) || (-default_h1_slope*(h1-best_h1)+(psnr-best_psnr)>0))
            {
                best_h1=h1;
                best_psnr=psnr;
                best_t=t;
                any_t_tried=true;
            }
        }
        ret_t=best_t;
        ret_h1=best_h1;
        ret_psnr=best_psnr;
    }

    void param_c::generate_config()
    {
        pivot_eb_ratio=0.208492;
        eb_ratio=0.793614;
        
        pivot_stride={1,1,1};
        vector<string> candidate_predictors={"cubic1_231","cubic1_132","cubic1_123","cubic2_231","cubic2_132","cubic2_123","cubic3_231","cubic3_132","cubic3_123"};
        for (uint64_t layer=0;layer<10;layer++)
        {
            float layer_eb=abs_eb*pow(eb_ratio,layer);
            float stat_eb=layer_eb*stat_eb_ratio;
            float neg_2_stat_eb=1/(2*stat_eb);
            bool any_predictor_tested=false;
            float best_t,best_h1,best_h2,best_psnr;
            string best_predictor;
            for (string &predictor:candidate_predictors)
            {
                float t=0;
                float h1,h2,psnr;
                generate_config2(t,h1,psnr,predictor,pivot_stride,layer_eb,stat_eb,neg_2_stat_eb);
                unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> A2B2_map;
                if (predictor.compare(0,6,"cubic1")==0)
                {
                    pivot_stride[0]*=2;
                    if ((predictor=="cubic1_231") && (data_shape[0]>4*pivot_stride[0]))
                    {
                        vector<vector<uint64_t>> block_loc={{5*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,pivot_stride[0]*data_shape[1]*data_shape[2],neg_2_stat_eb);
                    }
                    else if ((predictor=="cubic1_132") && (data_shape[0]>3*pivot_stride[0]) && (data_shape[1]>pivot_stride[1]))
                    {
                        vector<vector<uint64_t>> block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{pivot_stride[1],data_shape[1]},{0,data_shape[2]}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,pivot_stride[1]*data_shape[2],neg_2_stat_eb);
                    }
                    else if ((predictor=="cubic1_123") && (data_shape[0]>3*pivot_stride[0]) && (data_shape[2]>pivot_stride[2]))
                    {
                        vector<vector<uint64_t>> block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{pivot_stride[2],data_shape[2]}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,pivot_stride[2],neg_2_stat_eb);
                    }
                    pivot_stride[0]/=2;
                }
                else if (predictor.compare(0,6,"cubic2")==0)
                {
                    pivot_stride[1]*=2;
                    if ((predictor=="cubic2_231") && (data_shape[0]>pivot_stride[0]) && (data_shape[1]>3*pivot_stride[1]))
                    {
                        vector<vector<uint64_t>> block_loc={{pivot_stride[0],data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,pivot_stride[0]*data_shape[1]*data_shape[2],neg_2_stat_eb);
                    }
                    else if ((predictor=="cubic2_132") && (data_shape[1]>4*pivot_stride[1]))
                    {
                        vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{5*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,pivot_stride[1]*data_shape[2],neg_2_stat_eb);
                    }
                    else if ((predictor=="cubic2_123") && (data_shape[1]>3*pivot_stride[1]) && (data_shape[2]>pivot_stride[2]))
                    {
                        vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{pivot_stride[2],data_shape[2]}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,pivot_stride[2],neg_2_stat_eb);
                    }
                    pivot_stride[1]/=2;
                }
                else if (predictor.compare(0,6,"cubic3")==0)
                {
                    pivot_stride[2]*=2;
                    if ((predictor=="cubic3_231") && (data_shape[0]>3*pivot_stride[0]) && (data_shape[2]>3*pivot_stride[2]))
                    {
                        vector<vector<uint64_t>> block_loc={{pivot_stride[0],data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[2]/2,pivot_stride[0]*data_shape[1]*data_shape[2],neg_2_stat_eb);
                    }
                    else if ((predictor=="cubic3_132") && (data_shape[1]>pivot_stride[1]) && (data_shape[2]>3*pivot_stride[2]))
                    {
                        vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{pivot_stride[1],data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[2]/2,pivot_stride[1]*data_shape[2],neg_2_stat_eb);
                    }
                    else if ((predictor=="cubic3_123") && (data_shape[2]>4*pivot_stride[2]))
                    {
                        vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{0,data_shape[1]},{5*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
                        get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[2]/2,pivot_stride[2],neg_2_stat_eb);
                    }
                    pivot_stride[2]/=2;
                }
                if (A2B2_map.empty())
                    continue;
                uint64_t sampled_data_num=0;
                for (const auto &[AB_key,count]:A2B2_map)
                    sampled_data_num+=count;
                estimate_h2(h2,A2B2_map,t,layer_eb,stat_eb,sampled_data_num);
                if ((!any_predictor_tested) || (-default_h2_slope*(h2-best_h2)+(psnr-best_psnr)>0))
                {
                    best_t=t;
                    best_h1=h1;
                    best_h2=h2;
                    best_psnr=psnr;
                    best_predictor=predictor;
                    any_predictor_tested=true;
                }
            }
            printf("layer=%lu, best_predictor=%s, best_t=%f\n",layer,best_predictor.c_str(),best_t);
            predictor_vec.insert(predictor_vec.begin(),best_predictor);
            if (best_predictor.compare(0,6,"cubic1")==0)
                pivot_stride[0]*=2;
            else if (best_predictor.compare(0,6,"cubic2")==0)
                pivot_stride[1]*=2;
            else if (best_predictor.compare(0,6,"cubic3")==0)
                pivot_stride[2]*=2;
            printf("stride=%lu,%lu,%lu\n",pivot_stride[0],pivot_stride[1],pivot_stride[2]);
        }

        block_shape={pivot_stride[0]*4,pivot_stride[1]*4,pivot_stride[2]*4};
        for (int dim=0;dim<3;dim++)
            block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
    }
}