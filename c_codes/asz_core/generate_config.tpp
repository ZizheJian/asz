#pragma once

namespace asz
{
    void param_c::generate_config_enumerate()
    {
        //////// 用于搜索一个合适的config ////////
        if (!config_generated)
        {
            //////// 这里写初始配置 ////////

            //////// rel_eb=1e-5 ////////
            // block_shape={32,32,32};
            // pivot_stride={8,8,8};
            // pivot_eb_ratio=0.2023;
            // eb_ratio=0.960596;
            
            // for (int dim=0;dim<3;dim++)
            //     block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
            // for (int i=0;i<block_num[0]*block_num[1]*block_num[2];i++)
            //     predictor_vec.push_back({"cubic3","cubic1","cubic2","cubic1","cubic2","cubic3","cubic3","cubic2","cubic1"});

            //////// rel_eb=1e-4 ////////
            block_shape={32,64,32};
            pivot_stride={8,16,8};
            pivot_eb_ratio=0.208492;
            eb_ratio=0.793614;
            
            for (int dim=0;dim<3;dim++)
                block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
            for (int i=0;i<block_num[0]*block_num[1]*block_num[2];i++)
                predictor_vec.push_back({"cubic2","cubic1","cubic2","cubic3","cubic1","cubic2","cubic3","cubic1","cubic2","cubic3"});

            //////// rel_eb=1e-3 ////////
            // block_shape={32,32,32};
            // pivot_stride={8,8,8};
            // pivot_eb_ratio=0.1;
            
            // for (int dim=0;dim<3;dim++)
            //     block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
            // for (int i=0;i<block_num[0]*block_num[1]*block_num[2];i++)
            // {
            //     predictor_vec.push_back({"cubic2","cubic1","cubic3","cubic1","cubic2","cubic3","cubic3","cubic2","cubic1"});
            //     eb_ratio_vec.push_back({0.970299,0.990000,0.904382,0.990000,0.990000,0.904382,0.932065,0.990000,1.000000});
            // }

            //////// rel_eb=1e-1 ////////
            // block_shape={32,64,32};
            // pivot_stride={8,16,8};
            // pivot_eb_ratio=0.096161;
            
            // for (int dim=0;dim<3;dim++)
            //     block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
            // for (int i=0;i<block_num[0]*block_num[1]*block_num[2];i++)
            // {
            //     predictor_vec.push_back({"cubic1","cubic1","cubic1","cubic2","cubic2","cubic3","cubic2","cubic3","cubic2","cubic3"});
            //     eb_ratio_vec.push_back({1.000000,0.960596,0.980100,0.895338,0.980100,0.980100,0.886385,0.922745,0.970299,1.000000});
            // }

            config_generated=true;
            printf("pivot_eb_ratio=%f\n",pivot_eb_ratio);
            printf("eb_ratio=%f\n",eb_ratio);
            for (auto predictor:predictor_vec[0])
                printf("\"%s\",",predictor.c_str());
            printf("\n");
            
        }
        else
        {
            //////// 这里写搜索策略 ////////
            int step=(uint64_t)log2(pivot_stride[0])+(uint64_t)log2(pivot_stride[1])+(uint64_t)log2(pivot_stride[2]);
            while (true)
            {
                int change_pos=rand()%(step+1);
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
                else if (change_pos<step)
                {
                    //////// 交换predictor_vec ////////
                    // int idx=change_pos-1;
                    // if (predictor_vec[0][idx]!=predictor_vec[0][idx+1])
                    // {
                    //     swap(predictor_vec[0][idx],predictor_vec[0][idx+1]);
                    //     for (auto &vec:predictor_vec)
                    //         vec=predictor_vec[0];
                    //     break;
                    // }
                    // else
                    //     continue;
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
            for (auto predictor:predictor_vec[0])
                printf("\"%s\",",predictor.c_str());
            printf("\n");
        }
    }

    void param_c::generate_config()
    {
        pivot_eb_ratio=0.208492;
        eb_ratio=0.793614;
        
        pivot_stride={1,1,1};
        vector<string> possible_predictors={"cubic1","cubic2","cubic3"};
        predictor_vec.push_back(vector<string>());
        for (uint64_t layer=0;layer<10;layer++)
        {
            float layer_eb=abs_eb*pow(eb_ratio,layer);
            float stat_eb=0.01*abs_eb;
            float neg_2_stat_eb=1/(2*stat_eb);
            bool no_valid_result=true;
            float best_h1,best_psnr;
            string best_predictor;
            float best_t2;
            for (string &predictor:possible_predictors)
            {
                unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
                if (predictor=="cubic1")
                {
                    pivot_stride[0]*=2;
                    if (data_shape[0]>3*pivot_stride[0])
                    {
                        vector<vector<uint64_t>> block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
                        get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb);
                        // get_AB_map_random(AB_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb,layer_eb);
                    }
                    pivot_stride[0]/=2;
                }
                else if (predictor=="cubic2")
                {
                    pivot_stride[1]*=2;
                    if (data_shape[1]>3*pivot_stride[1])
                    {
                        vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
                        get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,neg_2_stat_eb);
                        // get_AB_map_random(AB_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,neg_2_stat_eb,layer_eb);
                    }
                    pivot_stride[1]/=2;
                }
                else if (predictor=="cubic3")
                {
                    pivot_stride[2]*=2;
                    if (data_shape[2]>3*pivot_stride[2])
                    {
                        vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
                        get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[2]/2,neg_2_stat_eb);
                        // get_AB_map_random(AB_map,data,block_loc,pivot_stride,pivot_stride[2]/2,neg_2_stat_eb,layer_eb);
                    }
                    pivot_stride[2]/=2;
                }
                if (AB_map.empty())
                    continue;
                uint64_t compressed_data_num=0;
                for (const auto &[AB_key,count]:AB_map)
                    compressed_data_num+=count;
                float h1=0,psnr=0;
                for (float t2:possible_t2_vec)
                {
                    estimate_br_psnr(h1,psnr,AB_map,t2,layer_eb,stat_eb,compressed_data_num);
                    if ((no_valid_result) || (-default_slope*(h1-best_h1)+(psnr-best_psnr)>0))
                    {
                        best_h1=h1;
                        best_psnr=psnr;
                        best_predictor=predictor;
                        best_t2=t2;
                        no_valid_result=false;
                    }
                }
            }
            printf("layer=%lu, best_predictor=%s, best_t2=%f\n",layer,best_predictor.c_str(),best_t2);
            predictor_vec[0].insert(predictor_vec[0].begin(),best_predictor);
            if (best_predictor=="cubic1")
                pivot_stride[0]*=2;
            else if (best_predictor=="cubic2")
                pivot_stride[1]*=2;
            else if (best_predictor=="cubic3")
                pivot_stride[2]*=2;
            printf("stride=%lu,%lu,%lu\n",pivot_stride[0],pivot_stride[1],pivot_stride[2]);
        }

        block_shape={pivot_stride[0]*4,pivot_stride[1]*4,pivot_stride[2]*4};
        for (int dim=0;dim<3;dim++)
            block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
        for (int i=1;i<block_num[0]*block_num[1]*block_num[2];i++)
            predictor_vec.push_back(predictor_vec[0]);
    }
}