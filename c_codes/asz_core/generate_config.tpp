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
        printf("slope_ratio=%.2f;\n",slope_ratio);
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
            //////// Nyx_baryon_density_center 1e-5 //////// 好
            // predictor_vec={"cubic2_120","cubic0_021","cubic1_120","cubic2_120","cubic0_012","cubic1_120","cubic2_021"};
            // pivot_eb_ratio=0.23;
            // eb_ratio=0.79;
            // slope_ratio=0.52;
            // block_pivot_ratio=2;
            //////// Nyx_baryon_density_center 1e-2 //////// 好
            // predictor_vec={"cubic2_021","cubic0_120","cubic1_021"};
            // pivot_eb_ratio=0.23;
            // eb_ratio=0.80;
            // slope_ratio=0.53;
            // block_pivot_ratio=2;

            //////// APSU_004_center 1e-5 //////// 好
            // predictor_vec={"cubic0_120"};
            // pivot_eb_ratio=0.24;
            // eb_ratio=0.83;
            // slope_ratio=0.53;
            // block_pivot_ratio=1;
            //////// APSU_004_center 1e-2 //////// 好
            // predictor_vec={"cubic0_120","cubic0_120","cubic0_120"};
            // pivot_eb_ratio=0.18;
            // eb_ratio=0.72;
            // slope_ratio=0.47;
            // block_pivot_ratio=6;

            //////// Pf01 1e-5 ////////
            // predictor_vec={"cubic2_012","cubic1_120","cubic2_021","cubic1_021","cubic2_021","cubic0_021"};
            // pivot_eb_ratio=0.28;
            // eb_ratio=0.81;
            // slope_ratio=0.54;
            // block_pivot_ratio=1;
            //////// Pf01 1e-2 ////////
            predictor_vec={"cubic0_120","cubic0_120","cubic1_120","cubic1_012","cubic1_012","cubic2_012"};
            pivot_eb_ratio=0.21;
            eb_ratio=0.79;
            slope_ratio=0.55;
            block_pivot_ratio=1;

            //////// CSSI_L0470_center 1e-3 ////////
            // predictor_vec={"cubic0_012","cubic1_120","cubic2_021","cubic2_012","cubic2_120","cubic1_012","cubic1_120","cubic2_120","cubic0_120","cubic2_120","cubic2_120","cubic2_120","cubic1_120","cubic0_012","cubic2_012","cubic1_012"};
            // pivot_eb_ratio=0.25;
            // eb_ratio=0.96;
            // slope_ratio=0.97;
            // block_pivot_ratio=3;

            //////// Miranda 1e-6 ////////
            // predictor_vec={"cubic2_120","cubic1_120","cubic1_120","cubic1_120","cubic2_120","cubic2_012","cubic2_120","cubic1_012","cubic2_012","cubic1_021","cubic1_021","cubic2_120","cubic2_120","cubic1_012","cubic0_120","cubic2_120","cubic1_012"};
            // pivot_eb_ratio=0.20;
            // eb_ratio=0.99;
            // block_pivot_ratio=2;

            //////// Miranda 1e-5 ////////
            // predictor_vec={"cubic1_021","cubic1_021","cubic2_012","cubic1_021","cubic1_012","cubic2_012","cubic2_012","cubic2_012","cubic1_012","cubic2_021","cubic2_120","cubic1_021","cubic1_021","cubic2_021","cubic2_120","cubic1_120","cubic0_120","cubic2_120","cubic1_012"};
            // pivot_eb_ratio=0.22;
            // eb_ratio=0.97;
            // slope_ratio=0.99;
            // block_pivot_ratio=2;

            //////// Miranda 1e-4 ////////
            // predictor_vec={"cubic2_120","cubic2_012","cubic1_012","cubic2_120","cubic1_021","cubic1_021","cubic2_120","cubic1_021","cubic2_021","cubic0_012","cubic2_120","cubic1_012"};
            // pivot_eb_ratio=0.23;
            // eb_ratio=0.85;
            // slope_ratio=0.5;
            // block_pivot_ratio=2;

            generate_pivot_stride_and_block_shape_and_block_num();
            config_generated=true;
            print_config();
        }
        else
        {
            //////// 这里写搜索策略 ////////
            // change_pos=0~predictor_vec.size()-1: 更改predictor_vec中的一个元素
            // change_pos=predictor_vec.size()~2*predictor_vec.size()-2: 将predictor_vec中的一个元素和前一个交换
            // change_pos=2*predictor_vec.size()-1: 更改predictor_vec的长度
            // change_pos=2*predictor_vec.size()+0: 更改pivot_eb_ratio
            // change_pos=2*predictor_vec.size()+1: 更改eb_ratio
            // change_pos=2*predictor_vec.size()+2: 更改slope_ratio
            // change_pos=2*predictor_vec.size()+3: 更改block_pivot_ratio
            int config_num=2*predictor_vec.size()+4;
            string change_operation;
            int change_pos=rand()%config_num;
            if (change_pos<=predictor_vec.size()-1)
                change_operation="change predictor_vec";
            else if (change_pos<=2*predictor_vec.size()-2)
            {
                change_operation="swap predictor_vec";
                change_pos-=predictor_vec.size();
                change_pos++;
            }
            else if (change_pos==2*predictor_vec.size()-1)
            {
                change_operation="change predictor_vec length";
                change_pos=0;
            }
            else if (change_pos==2*predictor_vec.size()+0)
            {
                change_operation="change pivot_eb_ratio";
                change_pos=0;
            }
            else if (change_pos==2*predictor_vec.size()+1)
            {
                change_operation="change eb_ratio";
                change_pos=0;
            }
            else if (change_pos==2*predictor_vec.size()+2)
            {
                change_operation="change slope_ratio";
                change_pos=0;
            }
            else if (change_pos==2*predictor_vec.size()+3)
            {                
                change_operation="change block_pivot_ratio";
                change_pos=0;
            }
            if (change_operation=="change predictor_vec")
            {
                string old_predictor=predictor_vec[change_pos];
                string new_perdictor=old_predictor;
                while (new_perdictor==old_predictor)
                    new_perdictor=candidate_predictors[rand()%candidate_predictors.size()];
                predictor_vec[change_pos]=new_perdictor;
                generate_pivot_stride_and_block_shape_and_block_num();
            }
            else if (change_operation=="swap predictor_vec")
                swap(predictor_vec[change_pos],predictor_vec[change_pos-1]);
            else if (change_operation=="change predictor_vec length")
            {
                int c=rand()%2;//0:减小，1:增大
                if (predictor_vec.size()==1)
                    predictor_vec.insert(predictor_vec.begin(),candidate_predictors[rand()%candidate_predictors.size()]);
                else if (c==0)
                    predictor_vec.erase(predictor_vec.begin());
                else if (c==1)
                    predictor_vec.insert(predictor_vec.begin(),candidate_predictors[rand()%candidate_predictors.size()]);
                generate_pivot_stride_and_block_shape_and_block_num();
            }
            else if (change_operation=="change pivot_eb_ratio")
            {
                int c=rand()%2;//0:减小，1:增大
                if (pivot_eb_ratio==1)
                    pivot_eb_ratio-=0.01;
                else if (pivot_eb_ratio==0)
                    pivot_eb_ratio+=0.01;
                else if (c==0)
                    pivot_eb_ratio-=0.01;
                else if (c==1)
                    pivot_eb_ratio+=0.01;
            }
            else if (change_operation=="change eb_ratio")
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
            }
            else if (change_operation=="change slope_ratio")
            {
                int c=rand()%2;//0:减小，1:增大
                if (slope_ratio==1)
                    slope_ratio-=0.01;
                else if (slope_ratio==0)
                    slope_ratio+=0.01;
                else if (c==0)
                    slope_ratio-=0.01;
                else if (c==1)
                    slope_ratio+=0.01;
            }
            else if (change_operation=="change block_pivot_ratio")
            {
                int c=rand()%2;//0:减小，1:增大
                if (block_pivot_ratio==1)
                    block_pivot_ratio++;
                else if (c==0)
                    block_pivot_ratio--;
                else if (c==1)
                    block_pivot_ratio++;
                generate_pivot_stride_and_block_shape_and_block_num();
            }
            print_config();
        }
    }

    void param_c::dot_sample_compress(vector<int64_t> &qb_vec,float &mse,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,float t,float eb,float neg_2_eb)
    {
        float pred;
        if (i<=half_stride)
        {
            if (i+half_stride>=right)
                pred=data[pos-dist];
            else if (i+3*half_stride>=right)
                pred=(data[pos-dist]+data[pos+dist])/2;
            else
                pred=(3*data[pos-dist]+6*data[pos+dist]-data[pos+3*dist])/8;
        }
        else
        {
            if (i+half_stride>=right)
                pred=(-data[pos-3*dist]+3*data[pos-dist])/2;
            else if (i+3*half_stride>=right)
                pred=(-data[pos-3*dist]+6*data[pos-dist]+3*data[pos+dist])/8;
            else 
            {
                pred=(0.25-t)*(data[pos-3*dist]+data[pos+3*dist]);
                pred+=(0.25+t)*(data[pos-dist]+data[pos+dist]);
            }
        }
        int64_t qb=llround((pred-data[pos])*neg_2_eb);
        qb_vec.push_back(qb);
        mse+=(pred-qb*2*eb-data[pos])*(pred-qb*2*eb-data[pos]);
    }

    void param_c::block_sample_compress_cubic0_120(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_loc(3);
        target_block_loc[0]=block_loc[0][0]+stride[0]/2;
        if (block_loc[1][0]==0)
            target_block_loc[1]=0;
        else
            target_block_loc[1]=block_loc[1][0]+stride[1];
        if (block_loc[2][0]==0)
            target_block_loc[2]=0;
        else
            target_block_loc[2]=block_loc[2][0]+stride[2];
        for (uint64_t i1=target_block_loc[1];i1<block_loc[1][1];i1+=sample_stride[1])
        for (uint64_t i2=target_block_loc[2];i2<block_loc[2][1];i2+=sample_stride[2])
        for (uint64_t i0=target_block_loc[0];i0<block_loc[0][1];i0+=sample_stride[0])
            dot_sample_compress(qb_vec,mse,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,
                stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic0_021(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_loc(3);
        target_block_loc[0]=block_loc[0][0]+stride[0]/2;
        if (block_loc[1][0]==0)
            target_block_loc[1]=0;
        else
            target_block_loc[1]=block_loc[1][0]+stride[1];
        if (block_loc[2][0]==0)
            target_block_loc[2]=0;
        else
            target_block_loc[2]=block_loc[2][0]+stride[2];
        for (uint64_t i0=target_block_loc[0];i0<block_loc[0][1];i0+=sample_stride[0])
        for (uint64_t i2=target_block_loc[2];i2<block_loc[2][1];i2+=sample_stride[2])
        for (uint64_t i1=target_block_loc[1];i1<block_loc[1][1];i1+=sample_stride[1])
            dot_sample_compress(qb_vec,mse,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,
                stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic0_012(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_loc(3);
        target_block_loc[0]=block_loc[0][0]+stride[0]/2;
        if (block_loc[1][0]==0)
            target_block_loc[1]=0;
        else
            target_block_loc[1]=block_loc[1][0]+stride[1];
        if (block_loc[2][0]==0)
            target_block_loc[2]=0;
        else
            target_block_loc[2]=block_loc[2][0]+stride[2];
        for (uint64_t i0=target_block_loc[0];i0<block_loc[0][1];i0+=sample_stride[0])
        for (uint64_t i1=target_block_loc[1];i1<block_loc[1][1];i1+=sample_stride[1])
        for (uint64_t i2=target_block_loc[2];i2<block_loc[2][1];i2+=sample_stride[2])
            dot_sample_compress(qb_vec,mse,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,
                stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic1_120(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_left(3);
        if (block_loc[0][0]==0)
            target_block_left[0]=0;
        else
            target_block_left[0]=block_loc[0][0]+stride[0];
        target_block_left[1]=block_loc[1][0]+stride[1]/2;
        if (block_loc[2][0]==0)
            target_block_left[2]=0;
        else
            target_block_left[2]=block_loc[2][0]+stride[2];
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=sample_stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=sample_stride[2])
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=sample_stride[0])
            dot_sample_compress(qb_vec,mse,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,
                stride[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic1_021(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_left(3);
        if (block_loc[0][0]==0)
            target_block_left[0]=0;
        else
            target_block_left[0]=block_loc[0][0]+stride[0];
        target_block_left[1]=block_loc[1][0]+stride[1]/2;
        if (block_loc[2][0]==0)
            target_block_left[2]=0;
        else
            target_block_left[2]=block_loc[2][0]+stride[2];
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=sample_stride[0])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=sample_stride[2])
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=sample_stride[1])
            dot_sample_compress(qb_vec,mse,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic1_012(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_left(3);
        if (block_loc[0][0]==0)
            target_block_left[0]=0;
        else
            target_block_left[0]=block_loc[0][0]+stride[0];
        target_block_left[1]=block_loc[1][0]+stride[1]/2;
        if (block_loc[2][0]==0)
            target_block_left[2]=0;
        else
            target_block_left[2]=block_loc[2][0]+stride[2];
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=sample_stride[0])
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=sample_stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=sample_stride[2])
            dot_sample_compress(qb_vec,mse,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic2_120(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_left(3);
        if (block_loc[0][0]==0)
            target_block_left[0]=0;
        else
            target_block_left[0]=block_loc[0][0]+stride[0];
        if (block_loc[1][0]==0)
            target_block_left[1]=0;
        else
            target_block_left[1]=block_loc[1][0]+stride[1];
        target_block_left[2]=block_loc[2][0]+stride[2]/2;
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=sample_stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=sample_stride[2])
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=sample_stride[0])
            dot_sample_compress(qb_vec,mse,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic2_021(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_left(3);
        if (block_loc[0][0]==0)
            target_block_left[0]=0;
        else
            target_block_left[0]=block_loc[0][0]+stride[0];
        if (block_loc[1][0]==0)
            target_block_left[1]=0;
        else
            target_block_left[1]=block_loc[1][0]+stride[1];
        target_block_left[2]=block_loc[2][0]+stride[2]/2;
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=sample_stride[0])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=sample_stride[2])
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=sample_stride[1])
            dot_sample_compress(qb_vec,mse,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_sample_compress_cubic2_012(vector<int64_t> &qb_vec,float &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
    {
        vector<uint64_t> target_block_left(3);
        if (block_loc[0][0]==0)
            target_block_left[0]=0;
        else
            target_block_left[0]=block_loc[0][0]+stride[0];
        if (block_loc[1][0]==0)
            target_block_left[1]=0;
        else
            target_block_left[1]=block_loc[1][0]+stride[1];
        target_block_left[2]=block_loc[2][0]+stride[2]/2;
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=sample_stride[0])
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=sample_stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=sample_stride[2])
            dot_sample_compress(qb_vec,mse,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb);
    }

    // 逐层生成配置
    // 对于每一层，先对每个predictor找到最好的t，然后用最好的t实际压缩得到br和psnr，选出最好的predictor
    void param_c::generate_config()
    {
        pivot_eb_ratio=0.23;
        eb_ratio=0.79;
        slope_ratio=0.52;
        block_pivot_ratio=2;
        
        pivot_stride={1,1,1};
        float cumulated_br=0;
        float cumulated_mse=0;
        float cumulated_psnr=0;
        uint64_t cumulated_data_num=0;

        string best_pivot_seq="";
        for (uint64_t layer=0;layer<8;layer++)
        {
            float layer_eb=abs_eb*pow(eb_ratio,layer);
            float neg_2_layer_eb=1/(2*layer_eb);
            float stat_eb=layer_eb*stat_eb_ratio;
            float neg_2_stat_eb=1/(2*stat_eb);
            float pivot_eb=abs_eb*pivot_eb_ratio;
            float layer_default_slope=default_slope*pow(slope_ratio,layer);
            unordered_map<string,unordered_map<float,float>> h1,psnr,dist;//每个predictor在不同t时的h1、psnr、dist
            unordered_map<string,float> best_t;//每个predictor最好的t
            unordered_map<string,float> qb_br,qb_mse,qb_psnr;//每个predictor在采样数据上的实测br、mse、psnr
            unordered_map<string,uint64_t> qb_num;//每个predictor的qb数量和pivot的qb数量
            for (string &predictor:candidate_predictors)
            {
                printf("predictor=%s\n",predictor.c_str());
                // 采样数据，得到AB_map
                vector<vector<uint64_t>> block_loc;
                unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
                if (predictor.compare(0,6,"cubic0")==0)
                {
                    pivot_stride[0]*=2;
                    block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
                    get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb);
                    pivot_stride[0]/=2;
                }
                else if (predictor.compare(0,6,"cubic1")==0)
                {
                    pivot_stride[1]*=2;
                    block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
                    get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,neg_2_stat_eb);
                    pivot_stride[1]/=2;
                }
                else if (predictor.compare(0,6,"cubic2")==0)
                {
                    pivot_stride[2]*=2;
                    block_loc={{0,data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
                    get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[2]/2,neg_2_stat_eb);
                    pivot_stride[2]/=2;
                }
                // 估算h1和psnr，找到最好的t
                if (AB_map.empty())
                {
                    best_t[predictor]=0.3125;
                    continue;
                }
                best_t[predictor]=candidate_t[0];
                for (auto t:candidate_t)
                {
                    get_h1_psnr(h1[predictor][t],psnr[predictor][t],AB_map,t,abs_eb,stat_eb);
                    dist[predictor][t]=-layer_default_slope*h1[predictor][t]+psnr[predictor][t];
                    if (dist[predictor][t]>dist[predictor][best_t[predictor]])
                        best_t[predictor]=t;
                }
                // 用最好的t实际压缩得到br和psnr
                uint64_t sample_stride=1;
                vector<int64_t> qb_vec;
                vector<int64_t> pivot_qb_vec;
                block_loc={{0,data_shape[0]},{0,data_shape[1]},{0,data_shape[2]}};
                if (predictor.compare(0,6,"cubic0")==0)
                {
                    pivot_stride[0]*=2;
                    if (predictor=="cubic0_120")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0],pivot_stride[1]*sample_stride,pivot_stride[2]*sample_stride};
                        block_sample_compress_cubic0_120(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic0_021")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*sample_stride,pivot_stride[1],pivot_stride[2]*sample_stride};
                        block_sample_compress_cubic0_021(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic0_012")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*sample_stride,pivot_stride[1]*sample_stride,pivot_stride[2]};
                        block_sample_compress_cubic0_012(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    pivot_stride[0]/=2;
                }
                else if (predictor.compare(0,6,"cubic1")==0)
                {
                    pivot_stride[1]*=2;
                    if (predictor=="cubic1_120")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0],pivot_stride[1]*sample_stride,pivot_stride[2]*sample_stride};
                        block_sample_compress_cubic1_120(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic1_021")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*sample_stride,pivot_stride[1],pivot_stride[2]*sample_stride};
                        block_sample_compress_cubic1_021(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic1_012")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*sample_stride,pivot_stride[1]*sample_stride,pivot_stride[2]};
                        block_sample_compress_cubic1_012(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    pivot_stride[1]/=2;
                }
                else if (predictor.compare(0,6,"cubic2")==0)
                {
                    pivot_stride[2]*=2;
                    if (predictor=="cubic2_120")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0],pivot_stride[1]*sample_stride,pivot_stride[2]*sample_stride};
                        block_sample_compress_cubic2_120(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic2_021")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*sample_stride,pivot_stride[1],pivot_stride[2]*sample_stride};
                        block_sample_compress_cubic2_021(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic2_012")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*sample_stride,pivot_stride[1]*sample_stride,pivot_stride[2]};
                        block_sample_compress_cubic2_012(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    pivot_stride[2]/=2;
                }
                //////// lossless compress qb ////////
                if (!qb_vec.empty())
                {
                    vector<unsigned char> huffman_bs_vec(data.size()*sizeof(float)*2);
                    unsigned char *huffman_bs=huffman_bs_vec.data();
                    huffman_encoder_class<int64_t> huffman_encoder;
                    huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
                    huffman_encoder.save(huffman_bs);
                    huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
                    uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
                    uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
                    vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
                    uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
                    zstd_bs_vec.resize(zstd_bs_len);
                    float cr=(float)qb_vec.size()*sizeof(float)/zstd_bs_len;
                    qb_br[predictor]=8*sizeof(float)/cr;
                    qb_mse[predictor]=qb_mse[predictor]/qb_vec.size();
                    qb_psnr[predictor]=10*log10((max_val-min_val)*(max_val-min_val)/qb_mse[predictor]);
                    qb_num[predictor]=qb_vec.size();
                }
            }
            string best_layer_predictor="";
            float best_dist=-1e8;
            for (auto &qb_predictor:candidate_predictors)
            {
                if (qb_num[qb_predictor]==0)
                    continue;
                float total_br=cumulated_br*cumulated_data_num+qb_br[qb_predictor]*qb_num[qb_predictor];
                float total_mse=cumulated_mse*cumulated_data_num+qb_mse[qb_predictor]*qb_num[qb_predictor];
                uint64_t total_num=cumulated_data_num+qb_num[qb_predictor];
                total_br/=total_num;
                total_mse/=total_num;
                float total_psnr=10*log10((max_val-min_val)*(max_val-min_val)/total_mse);
                printf("qb_predictor=%s\n",qb_predictor.c_str());
                printf("    cumulated_br=%f, cumulated_psnr=%f, cumulated_data_num=%lu\n",cumulated_br,10*log10((max_val-min_val)*(max_val-min_val)/cumulated_mse),cumulated_data_num);
                printf("    qb_br=%f, qb_psnr=%f, qb_num=%lu, qb_dist=%f\n",qb_br[qb_predictor],qb_psnr[qb_predictor],qb_num[qb_predictor],-layer_default_slope*qb_br[qb_predictor]+qb_psnr[qb_predictor]);
                printf("    total_br=%f, total_psnr=%f, total_num=%lu\n",total_br,total_psnr,total_num);
                printf("    dist=%f\n",-layer_default_slope*total_br+total_psnr);
                if (best_layer_predictor=="" || -layer_default_slope*qb_br[qb_predictor]+qb_psnr[qb_predictor]>best_dist)
                {
                    best_dist=-layer_default_slope*qb_br[qb_predictor]+qb_psnr[qb_predictor];
                    best_layer_predictor=qb_predictor;
                }
            }
            printf("best_layer_predictor=%s\n",best_layer_predictor.c_str());
            cumulated_br=(cumulated_br*cumulated_data_num+qb_br[best_layer_predictor]*qb_num[best_layer_predictor])/(cumulated_data_num+qb_num[best_layer_predictor]);
            cumulated_mse=(cumulated_mse*cumulated_data_num+qb_mse[best_layer_predictor]*qb_num[best_layer_predictor])/(cumulated_data_num+qb_num[best_layer_predictor]);
            cumulated_psnr=10*log10((max_val-min_val)*(max_val-min_val)/cumulated_mse);
            cumulated_data_num+=qb_num[best_layer_predictor];
            if (best_layer_predictor.compare(0,6,"cubic0")==0)
                pivot_stride[0]*=2;
            else if (best_layer_predictor.compare(0,6,"cubic1")==0)
                pivot_stride[1]*=2;
            else if (best_layer_predictor.compare(0,6,"cubic2")==0)
                pivot_stride[2]*=2;
            predictor_vec.insert(predictor_vec.begin(),best_layer_predictor);
        }
        generate_pivot_stride_and_block_shape_and_block_num();
    }
}