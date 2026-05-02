#pragma once

namespace asz
{
    void param_c::print_config()
    {
        printf("predictor_vec={");
        for (auto predictor_it=predictor_vec.begin();predictor_it!=predictor_vec.end();predictor_it++)
            if (predictor_it==predictor_vec.end()-1)
                printf("\"%s\"",predictor_it->c_str());
            else
                printf("\"%s\",",predictor_it->c_str());
        printf("};\n");
        printf("pivot_eb_ratio=%.2f;\n",pivot_eb_ratio);
        printf("eb_ratio=%.2f;\n",eb_ratio);
        printf("block_pivot_ratio=%lu;\n",block_pivot_ratio);
        printf("pivot_stride={%lu,%lu,%lu};\n",pivot_stride[0],pivot_stride[1],pivot_stride[2]);
        printf("block_shape={%lu,%lu,%lu};\n",block_shape[0],block_shape[1],block_shape[2]);
        printf("block_num={%lu,%lu,%lu};\n",block_num[0],block_num[1],block_num[2]);
    }

    void param_c::generate_pivot_stride_and_block_shape_and_block_num()
    {
        pivot_stride={1,1,1};
        for (auto predictor:predictor_vec)
        {
            if (predictor.compare(0,6,"cubic0")==0)
                pivot_stride[0]*=2;
            else if (predictor.compare(0,6,"cubic1")==0)
                pivot_stride[1]*=2;
            else if (predictor.compare(0,6,"cubic2")==0)
                pivot_stride[2]*=2;
        }
        block_shape={pivot_stride[0]*block_pivot_ratio,pivot_stride[1]*block_pivot_ratio,pivot_stride[2]*block_pivot_ratio};
        block_num={(data_shape[0]+block_shape[0]-1)/block_shape[0],
            (data_shape[1]+block_shape[1]-1)/block_shape[1],
            (data_shape[2]+block_shape[2]-1)/block_shape[2]};
    }

    void param_c::generate_config_enumerate()
    {
        //////// 用于搜索一个合适的config ////////
        if (!config_generated)
        {
            //////// 这里写初始配置 ////////
            predictor_vec={"cubic1_021","cubic1_021","cubic2_021","cubic2_021","cubic2_012","cubic2_021","cubic2_012","cubic2_012","cubic1_021","cubic2_021","cubic2_012","cubic1_012","cubic0_012","cubic2_120","cubic1_012"};
            pivot_eb_ratio=0.20;
            eb_ratio=0.99;
            block_pivot_ratio=2;

            generate_pivot_stride_and_block_shape_and_block_num();
            config_generated=true;
            print_config();
        }
        else
        {
            //////// 这里写搜索策略 ////////
            // change_pos=0~predictor_vec.size()-1: 更改predictor_vec中的一个元素
            // change_pos=predictor_vec.size(): 更改pivot_eb_ratio
            // change_pos=predictor_vec.size()+1: 更改eb_ratio
            // change_pos=predictor_vec.size()+2: 更改block_pivot_ratio
            // change_pos=predictor_vec.size()+3: 更改predictor_vec的长度
            int config_num=predictor_vec.size()+4;
            while (true)
            {
                int change_pos=rand()%config_num;
                if (change_pos<predictor_vec.size())
                {
                    string old_predictor=predictor_vec[change_pos];
                    string new_perdictor=old_predictor;
                    while (new_perdictor==old_predictor)
                        new_perdictor=candidate_predictors[rand()%candidate_predictors.size()];
                    predictor_vec[change_pos]=new_perdictor;
                    generate_pivot_stride_and_block_shape_and_block_num();
                    break;
                }
                if (change_pos==predictor_vec.size())
                {
                    //////// 改变pivot_eb_ratio ////////
                    int c=rand()%2;//0:减小，1:增大
                    if (pivot_eb_ratio==1)
                        pivot_eb_ratio-=0.01;
                    else if (pivot_eb_ratio==0)
                        pivot_eb_ratio+=0.01;
                    else if (c==0)
                        pivot_eb_ratio-=0.01;
                    else if (c==1)
                        pivot_eb_ratio+=0.01;
                    break;
                }
                if (change_pos==predictor_vec.size()+1)
                {
                    int c=rand()%2;//0:减小，1:增大
                    if (eb_ratio==1)
                        eb_ratio-=0.01;
                    else if (eb_ratio==0)
                        eb_ratio+=0.01;
                    else if (c==0)
                        eb_ratio-=0.01;
                    else if (c==1)
                        eb_ratio+=0.01;
                    break;
                }
                if (change_pos==predictor_vec.size()+2)
                {
                    //////// 改变block_pivot_ratio ////////
                    int c=rand()%2;//0:减小，1:增大
                    if (block_pivot_ratio==1)
                        block_pivot_ratio++;
                    else if (c==0)
                        block_pivot_ratio--;
                    else if (c==1)
                        block_pivot_ratio++;
                    generate_pivot_stride_and_block_shape_and_block_num();
                    break;
                }
                if (change_pos==predictor_vec.size()+3)
                {
                    int c=rand()%2;//0:减小，1:增大
                    if (predictor_vec.size()==1)
                        predictor_vec.insert(predictor_vec.begin(),candidate_predictors[rand()%candidate_predictors.size()]);
                    else if (c==0)
                        predictor_vec.erase(predictor_vec.begin());
                    else if (c==1)
                        predictor_vec.insert(predictor_vec.begin(),candidate_predictors[rand()%candidate_predictors.size()]);
                    generate_pivot_stride_and_block_shape_and_block_num();
                    break;
                }
            }
            print_config();
        }
    }

    // void param_c::generate_config2(float &ret_t,float &ret_h1,float &ret_psnr,string &predictor,vector<uint64_t> &stride,float abs_eb,float stat_eb,float neg_2_stat_eb)
    // {
    //     // 由generate_config调用，用于找到一个stencil pattern最好的t
    //     unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
    //     vector<vector<uint64_t>> block_loc;
    //     if ((predictor.compare(0,6,"cubic1")==0) && (data_shape[0]>6*stride[0]))
    //     {
    //         stride[0]*=2;
    //         block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
    //         get_AB_map(AB_map,data,block_loc,stride,data_shape[1]*data_shape[2],neg_2_stat_eb);
    //         stride[0]/=2;
    //     }
    //     else if ((predictor.compare(0,6,"cubic2")==0) && (data_shape[1]>6*stride[1]))
    //     {
    //         stride[1]*=2;
    //         block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
    //         get_AB_map(AB_map,data,block_loc,stride,data_shape[2],neg_2_stat_eb);
    //         stride[1]/=2;
    //     }
    //     else if ((predictor.compare(0,6,"cubic3")==0) && (data_shape[2]>6*stride[2]))
    //     {
    //         stride[2]*=2;
    //         block_loc={{0,data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
    //         get_AB_map(AB_map,data,block_loc,stride,1,neg_2_stat_eb);
    //         stride[2]/=2;
    //     }
    //     if (AB_map.empty())
    //     {
    //         ret_t=0.25;
    //         return;
    //     }
    //     uint64_t sampled_data_num=0;
    //     for (const auto &[AB_key,count]:AB_map)
    //         sampled_data_num+=count;

    //     bool any_t_tried=false;
    //     float best_t,best_h1,best_psnr;
    //     for (float t:possible_t_vec)
    //     {
    //         float h1,psnr;
    //         float neg_2_eb=1/(2*abs_eb);
    //         estimate_h1_psnr(h1,psnr,AB_map,t,abs_eb,stat_eb,sampled_data_num);
    //         if ((!any_t_tried) || (-default_h1_slope*(h1-best_h1)+(psnr-best_psnr)>0))
    //         {
    //             best_h1=h1;
    //             best_psnr=psnr;
    //             best_t=t;
    //             any_t_tried=true;
    //         }
    //     }
    //     ret_t=best_t;
    //     ret_h1=best_h1;
    //     ret_psnr=best_psnr;
    // }

    // void param_c::generate_config()
    // {
    //     pivot_eb_ratio=0.208492;
    //     eb_ratio=0.793614;
        
    //     pivot_stride={1,1,1};
    //     vector<string> candidate_predictors={"cubic1_231","cubic1_132","cubic1_123","cubic2_231","cubic2_132","cubic2_123","cubic3_231","cubic3_132","cubic3_123"};
    //     for (uint64_t layer=0;layer<10;layer++)
    //     {
    //         float layer_eb=abs_eb*pow(eb_ratio,layer);
    //         float stat_eb=layer_eb*stat_eb_ratio;
    //         float neg_2_stat_eb=1/(2*stat_eb);
    //         bool any_predictor_tested=false;
    //         float best_t,best_h1,best_h2,best_psnr;
    //         string best_predictor;
    //         for (string &predictor:candidate_predictors)
    //         {
    //             float t=0;
    //             float h1,h2,psnr;
    //             generate_config2(t,h1,psnr,predictor,pivot_stride,layer_eb,stat_eb,neg_2_stat_eb);
    //             unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> A2B2_map;
    //             if (predictor.compare(0,6,"cubic1")==0)
    //             {
    //                 pivot_stride[0]*=2;
    //                 if ((predictor=="cubic1_231") && (data_shape[0]>4*pivot_stride[0]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{5*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,pivot_stride[0]*data_shape[1]*data_shape[2],neg_2_stat_eb);
    //                 }
    //                 else if ((predictor=="cubic1_132") && (data_shape[0]>3*pivot_stride[0]) && (data_shape[1]>pivot_stride[1]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{pivot_stride[1],data_shape[1]},{0,data_shape[2]}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,pivot_stride[1]*data_shape[2],neg_2_stat_eb);
    //                 }
    //                 else if ((predictor=="cubic1_123") && (data_shape[0]>3*pivot_stride[0]) && (data_shape[2]>pivot_stride[2]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{pivot_stride[2],data_shape[2]}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,pivot_stride[2],neg_2_stat_eb);
    //                 }
    //                 pivot_stride[0]/=2;
    //             }
    //             else if (predictor.compare(0,6,"cubic2")==0)
    //             {
    //                 pivot_stride[1]*=2;
    //                 if ((predictor=="cubic2_231") && (data_shape[0]>pivot_stride[0]) && (data_shape[1]>3*pivot_stride[1]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{pivot_stride[0],data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,pivot_stride[0]*data_shape[1]*data_shape[2],neg_2_stat_eb);
    //                 }
    //                 else if ((predictor=="cubic2_132") && (data_shape[1]>4*pivot_stride[1]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{5*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,pivot_stride[1]*data_shape[2],neg_2_stat_eb);
    //                 }
    //                 else if ((predictor=="cubic2_123") && (data_shape[1]>3*pivot_stride[1]) && (data_shape[2]>pivot_stride[2]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{pivot_stride[2],data_shape[2]}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,pivot_stride[2],neg_2_stat_eb);
    //                 }
    //                 pivot_stride[1]/=2;
    //             }
    //             else if (predictor.compare(0,6,"cubic3")==0)
    //             {
    //                 pivot_stride[2]*=2;
    //                 if ((predictor=="cubic3_231") && (data_shape[0]>3*pivot_stride[0]) && (data_shape[2]>3*pivot_stride[2]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{pivot_stride[0],data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[2]/2,pivot_stride[0]*data_shape[1]*data_shape[2],neg_2_stat_eb);
    //                 }
    //                 else if ((predictor=="cubic3_132") && (data_shape[1]>pivot_stride[1]) && (data_shape[2]>3*pivot_stride[2]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{pivot_stride[1],data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[2]/2,pivot_stride[1]*data_shape[2],neg_2_stat_eb);
    //                 }
    //                 else if ((predictor=="cubic3_123") && (data_shape[2]>4*pivot_stride[2]))
    //                 {
    //                     vector<vector<uint64_t>> block_loc={{0,data_shape[0]},{0,data_shape[1]},{5*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
    //                     get_A2B2_map(A2B2_map,data,block_loc,pivot_stride,pivot_stride[2]/2,pivot_stride[2],neg_2_stat_eb);
    //                 }
    //                 pivot_stride[2]/=2;
    //             }
    //             if (A2B2_map.empty())
    //                 continue;
    //             uint64_t sampled_data_num=0;
    //             for (const auto &[AB_key,count]:A2B2_map)
    //                 sampled_data_num+=count;
    //             estimate_h2(h2,A2B2_map,t,layer_eb,stat_eb,sampled_data_num);
    //             if ((!any_predictor_tested) || (-default_h2_slope*(h2-best_h2)+(psnr-best_psnr)>0))
    //             {
    //                 best_t=t;
    //                 best_h1=h1;
    //                 best_h2=h2;
    //                 best_psnr=psnr;
    //                 best_predictor=predictor;
    //                 any_predictor_tested=true;
    //             }
    //         }
    //         printf("layer=%lu, best_predictor=%s, best_t=%f\n",layer,best_predictor.c_str(),best_t);
    //         predictor_vec.insert(predictor_vec.begin(),best_predictor);
    //         if (best_predictor.compare(0,6,"cubic1")==0)
    //             pivot_stride[0]*=2;
    //         else if (best_predictor.compare(0,6,"cubic2")==0)
    //             pivot_stride[1]*=2;
    //         else if (best_predictor.compare(0,6,"cubic3")==0)
    //             pivot_stride[2]*=2;
    //         printf("stride=%lu,%lu,%lu\n",pivot_stride[0],pivot_stride[1],pivot_stride[2]);
    //     }

    //     block_shape={pivot_stride[0]*4,pivot_stride[1]*4,pivot_stride[2]*4};
    //     for (int dim=0;dim<3;dim++)
    //         block_num.push_back((data_shape[dim]+block_shape[dim]-1)/block_shape[dim]);
    // }
}