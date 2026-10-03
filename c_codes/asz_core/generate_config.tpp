#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::print_config()
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
        printf("max_layer_num=%lu;\n",max_layer_num);
        printf("full_predictor_search_layer_num=%lu;\n",full_predictor_search_layer_num);
        printf("generate_config_sample_stride=%lu;\n",generate_config_sample_stride);
        printf("h1_block_sampling_num=%lu;\n",h1_block_sampling_num);
        printf("stat_eb_ratio=%.3f;\n",stat_eb_ratio);
        printf("predictor_family_sample_limit=%lu;\n",predictor_family_sample_limit);
        printf("predictor_family_mse_ratio_threshold=%.6f;\n",predictor_family_mse_ratio_threshold);
        printf("default_slope_invalid_ratio_threshold=%.3f;\n",default_slope_invalid_ratio_threshold);
        printf("default_slope_fallback=%.6f;\n",default_slope_fallback);
        printf("default_slope_eb_span=%.6f;\n",default_slope_eb_span);
        printf("t_precision=%d;\n",t_precision);
        printf("t_range=[%.6f,%.6f];\n",t_min,t_max);
        printf("t_candidates={");
        for (auto candidate_it=candidate_t.begin();candidate_it!=candidate_t.end();candidate_it++)
            printf("%s%.6f",candidate_it==candidate_t.begin()?"":",",*candidate_it);
        printf("};\n");
        printf("block_t_candidates={");
        for (auto candidate_it=block_candidate_t.begin();candidate_it!=block_candidate_t.end();candidate_it++)
            printf("%s%.6f",candidate_it==block_candidate_t.begin()?"":",",*candidate_it);
        printf("};\n");
        printf("block_pivot_ratio=%lu;\n",block_pivot_ratio);
        printf("t_policy=%s;\n",t_policy.c_str());
        printf("block_t_policy=%s;\n",block_t_policy.c_str());
        printf("predictor_family=%s;\n",force_quintic?"quintic":"cubic");
        printf("pivot_stride={%lu,%lu,%lu};\n",pivot_stride[0],pivot_stride[1],pivot_stride[2]);
        printf("block_shape={%lu,%lu,%lu};\n",block_shape[0],block_shape[1],block_shape[2]);
        printf("block_num={%lu,%lu,%lu};\n",block_num[0],block_num[1],block_num[2]);
    }

    template<typename T>
    void param_c<T>::select_predictor_family()
    {
        auto start_time=chrono::high_resolution_clock::now();
        if (predictor_vec.empty())
            throw runtime_error("cannot select predictor family without a predictor plan");
        int direction=predictor_vec.back()[5]-'0';
        uint64_t direction_size=data_shape[direction]/2;
        if (direction_size==0)
        {
            force_quintic=false;
            printf("Predictor family selection: direction=%d, no final-layer samples, family=cubic\n",direction);
            auto end_time=chrono::high_resolution_clock::now();
            printf("Predictor family selection time: %f s\n",chrono::duration<double>(end_time-start_time).count());
            return;
        }
        uint64_t sample_space=direction_size;
        for (int axis=0;axis<3;axis++)
            if (axis!=direction)
                sample_space*=data_shape[axis];
        uint64_t sample_num=min(sample_space,predictor_family_sample_limit);
        mt19937_64 random_generator(0);
        long double cubic_squared_error=0,quintic_squared_error=0;
        auto evaluate_sample=[&](uint64_t logical_index)
        {
            uint64_t coordinate[3];
            for (int axis=2;axis>=0;axis--)
            {
                uint64_t axis_size=axis==direction?direction_size:data_shape[axis];
                coordinate[axis]=logical_index%axis_size;
                logical_index/=axis_size;
            }
            coordinate[direction]=2*coordinate[direction]+1;
            uint64_t pos=coordinate[0]*data_shape[1]*data_shape[2]+coordinate[1]*data_shape[2]+coordinate[2];
            uint64_t dist=direction==0?data_shape[1]*data_shape[2]:direction==1?data_shape[2]:1;
            uint64_t block_id=coordinate[direction]/block_shape[direction];
            uint64_t right=min((block_id+1)*block_shape[direction]+1,data_shape[direction]);
            uint64_t i=coordinate[direction];
            double cubic_prediction;
            if (i<=1)
            {
                if (i+1>=right)
                    cubic_prediction=data[pos-dist];
                else if (i+3>=right)
                    cubic_prediction=((double)data[pos-dist]+data[pos+dist])/2;
                else
                    cubic_prediction=(3*(double)data[pos-dist]+6*(double)data[pos+dist]-data[pos+3*dist])/8;
            }
            else if (i+1>=right)
                cubic_prediction=(-(double)data[pos-3*dist]+3*(double)data[pos-dist])/2;
            else if (i+3>=right)
                cubic_prediction=(-(double)data[pos-3*dist]+6*(double)data[pos-dist]+3*(double)data[pos+dist])/8;
            else
                cubic_prediction=-(data[pos-3*dist]+(double)data[pos+3*dist])/16+9*(data[pos-dist]+(double)data[pos+dist])/16;
            double quintic_prediction=cubic_prediction;
            if (i>=5&&i+5<right)
                quintic_prediction=(75.0/128)*(data[pos-dist]+(double)data[pos+dist])-(25.0/256)*(data[pos-3*dist]+(double)data[pos+3*dist])+(3.0/256)*(data[pos-5*dist]+(double)data[pos+5*dist]);
            long double cubic_error=cubic_prediction-(double)data[pos];
            long double quintic_error=quintic_prediction-(double)data[pos];
            cubic_squared_error+=cubic_error*cubic_error;
            quintic_squared_error+=quintic_error*quintic_error;
        };
        if (sample_num==sample_space)
            for (uint64_t sample_id=0;sample_id<sample_num;sample_id++)
                evaluate_sample(sample_id);
        else
            for (uint64_t sample_id=0;sample_id<sample_num;sample_id++)
            {
                uint64_t segment_begin=(uint64_t)((unsigned __int128)sample_id*sample_space/sample_num);
                uint64_t segment_end=(uint64_t)((unsigned __int128)(sample_id+1)*sample_space/sample_num);
                evaluate_sample(segment_begin+random_generator()%(segment_end-segment_begin));
            }
        force_quintic=quintic_squared_error<cubic_squared_error*predictor_family_mse_ratio_threshold;
        printf("Predictor family selection: direction=%d, samples=%lu, cubic_mse=%.12Le, quintic_mse=%.12Le, family=%s\n",direction,sample_num,cubic_squared_error/sample_num,quintic_squared_error/sample_num,force_quintic?"quintic":"cubic");
        auto end_time=chrono::high_resolution_clock::now();
        printf("Predictor family selection time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    }

    template<typename T>
    void param_c<T>::generate_pivot_stride_and_block_shape_and_block_num()
    {
        pivot_stride={1,1,1};
        for (auto predictor:predictor_vec)
        {
            if (predictor.substr(0,6)=="cubic0")
                pivot_stride[0]*=2;
            else if (predictor.substr(0,6)=="cubic1")
                pivot_stride[1]*=2;
            else if (predictor.substr(0,6)=="cubic2")
                pivot_stride[2]*=2;
        }
        block_shape={pivot_stride[0]*block_pivot_ratio,pivot_stride[1]*block_pivot_ratio,pivot_stride[2]*block_pivot_ratio};
        block_num={(data_shape[0]+block_shape[0]-1)/block_shape[0],
            (data_shape[1]+block_shape[1]-1)/block_shape[1],
            (data_shape[2]+block_shape[2]-1)/block_shape[2]};
    }

    template<typename T>
    void param_c<T>::generate_config_enumerate()
    {
        //////// 用于搜索一个合适的config ////////
        if (!config_generated)
        {
            //////// 这里写初始配置 ////////
            //////// videollava 1e-4 ////////
            predictor_vec={"cubic1_012","cubic1_021","cubic1_021","cubic0_021","cubic1_021","cubic1_120","cubic0_120","cubic0_120"};
            pivot_eb_ratio=0.12;
            eb_ratio=0.77;
            slope_ratio=0.55;
            block_pivot_ratio=5;
            //////// videollava 1e-2 ////////
            predictor_vec={"cubic2_120","cubic2_021","cubic2_120","cubic2_012","cubic2_021","cubic1_120","cubic1_120","cubic1_120","cubic0_012","cubic0_012","cubic0_012"};
            pivot_eb_ratio=0.10;
            eb_ratio=0.74;
            slope_ratio=0.54;
            block_pivot_ratio=6;

            //////// Pf01 1e-5 ////////
            // predictor_vec={"cubic1_012","cubic2_021","cubic0_120","cubic1_120","cubic0_120","cubic1_120","cubic0_012","cubic1_120","cubic2_120","cubic0_012","cubic2_120","cubic1_120"};
            // pivot_eb_ratio=0.11;
            // eb_ratio=0.71;
            // slope_ratio=0.53;
            // block_pivot_ratio=3;
            //////// Pf01 1e-3 ////////
            // predictor_vec={"cubic1_021","cubic2_012","cubic1_120","cubic0_120","cubic1_120","cubic2_120","cubic0_012","cubic2_120","cubic1_120","cubic0_120"};
            // pivot_eb_ratio=0.11;
            // eb_ratio=0.70;
            // slope_ratio=0.54;
            // block_pivot_ratio=2;

            //////// CLDICE_center 1e-5 ////////
            // predictor_vec={"cubic1_021","cubic2_012","cubic1_012","cubic2_021","cubic1_021","cubic2_021"};
            // pivot_eb_ratio=0.14;
            // eb_ratio=0.74;
            // slope_ratio=0.52;
            // block_pivot_ratio=1;
            //////// CLDICE_center 1e-3 ////////
            // predictor_vec={"cubic2_021","cubic2_021","cubic2_021","cubic1_012","cubic2_012","cubic1_012","cubic2_012","cubic1_012","cubic2_021","cubic1_012","cubic2_021"};
            // pivot_eb_ratio=0.09;
            // eb_ratio=0.71;
            // slope_ratio=0.47;
            // block_pivot_ratio=5;

            //////// Nyx_baryon_density_center 1e-5 //////// 好
            // predictor_vec={"cubic2_120","cubic1_012","cubic2_021","cubic0_120","cubic1_120","cubic2_021","cubic0_120","cubic1_120","cubic2_120"};
            // pivot_eb_ratio=0.10;
            // eb_ratio=0.71;
            // slope_ratio=0.53;
            // block_pivot_ratio=4;
            //////// Nyx_baryon_density_center 1e-3 //////// 好
            // predictor_vec={"cubic0_012","cubic1_120","cubic1_012","cubic2_021","cubic0_012","cubic1_021","cubic2_012","cubic0_012","cubic0_012","cubic1_012","cubic2_012"};
            // pivot_eb_ratio=0.07;
            // eb_ratio=0.71;
            // slope_ratio=0.54;
            // block_pivot_ratio=3;

            

            //////// APSU_004_center 1e-5 //////// 好
            // predictor_vec={"cubic0_120"};
            // pivot_eb_ratio=0.22;
            // eb_ratio=0.85;
            // slope_ratio=0.47;
            // block_pivot_ratio=9;
            //////// APSU_004_center 1e-3 //////// 好
            // predictor_vec={"cubic0_120","cubic0_120","cubic0_120"};
            // pivot_eb_ratio=0.17;
            // eb_ratio=0.78;
            // slope_ratio=0.48;
            // block_pivot_ratio=8;

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

    template<typename T>
    void param_c<T>::dot_sample_compress(vector<qb_t> &qb_vec,T &mse,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,T neg_2_eb)
    {
        T pred;
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
        qb_t qb=(qb_t)llround((pred-data[pos])*neg_2_eb);
        qb_vec.push_back(qb);
        mse+=(pred-qb*2*eb-data[pos])*(pred-qb*2*eb-data[pos]);
    }

    template<typename T>
    void param_c<T>::block_sample_compress_cubic0_120(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic0_021(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic0_012(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic1_120(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic1_021(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic1_012(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic2_120(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic2_021(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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

    template<typename T>
    void param_c<T>::block_sample_compress_cubic2_012(vector<qb_t> &qb_vec,T &mse,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &sample_stride,
        vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
    // 尝试使用固定的t而不是最好的t
    template<typename T>
    void param_c<T>::generate_config(string task)
    {
        if (task=="compress");
        else if (task=="decompress")
            return;
        else
            throw invalid_argument("invalid task received in generate_config");
        
        auto start_time=chrono::high_resolution_clock::now();
        
        pivot_stride={1,1,1};
        for (uint64_t layer=0;layer<max_layer_num;layer++)
        {
            T layer_eb=abs_eb*pow(eb_ratio,layer);
            T neg_2_layer_eb=1/(2*layer_eb);
            T stat_eb=layer_eb*stat_eb_ratio;
            T neg_2_stat_eb=1/(2*stat_eb);
            T layer_default_slope=default_slope*pow(slope_ratio,layer);
            vector<string> layer_candidate_predictors;
            if (layer<full_predictor_search_layer_num)
                layer_candidate_predictors=candidate_predictors;
            else
                layer_candidate_predictors={"cubic0_012","cubic1_012","cubic2_012"};
            unordered_map<string,unordered_map<T,T>> h1,psnr,dist;//每个predictor在不同t时的h1、psnr、dist
            unordered_map<string,T> best_t;//每个predictor最好的t
            unordered_map<string,T> qb_br,qb_mse,qb_psnr;//每个predictor在采样数据上的实测br、mse、psnr
            unordered_map<string,uint64_t> qb_num;//每个predictor的qb数量和pivot的qb数量
            for (string &predictor:layer_candidate_predictors)
            {
                // 采样数据，得到AB_map
                vector<vector<uint64_t>> block_loc;
                unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
                if ((predictor.substr(0,6)=="cubic0") and (data_shape[0]>3*pivot_stride[0]))
                {
                    pivot_stride[0]*=2;
                    block_loc={{3*pivot_stride[0]/2,data_shape[0]-3*pivot_stride[0]/2},{0,data_shape[1]},{0,data_shape[2]}};
                    get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb);
                    pivot_stride[0]/=2;
                }
                else if ((predictor.substr(0,6)=="cubic1") and (data_shape[1]>3*pivot_stride[1]))
                {
                    pivot_stride[1]*=2;
                    block_loc={{0,data_shape[0]},{3*pivot_stride[1]/2,data_shape[1]-3*pivot_stride[1]/2},{0,data_shape[2]}};
                    get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[1]*data_shape[2]/2,neg_2_stat_eb);
                    pivot_stride[1]/=2;
                }
                else if ((predictor.substr(0,6)=="cubic2") and (data_shape[2]>3*pivot_stride[2]))
                {
                    pivot_stride[2]*=2;
                    block_loc={{0,data_shape[0]},{0,data_shape[1]},{3*pivot_stride[2]/2,data_shape[2]-3*pivot_stride[2]/2}};
                    get_AB_map(AB_map,data,block_loc,pivot_stride,pivot_stride[2]/2,neg_2_stat_eb);
                    pivot_stride[2]/=2;
                }
                // 估算h1和psnr，找到最好的t
                T initial_t=t_policy=="adaptive"?(T)4/16:candidate_t.front();
                if (AB_map.empty())
                    best_t[predictor]=initial_t;
                else
                {
                    best_t[predictor]=initial_t;
                    get_h1_psnr(h1[predictor][initial_t],psnr[predictor][initial_t],AB_map,initial_t,layer_eb,stat_eb);
                    dist[predictor][initial_t]=-layer_default_slope*h1[predictor][initial_t]+psnr[predictor][initial_t];
                    for (auto t:candidate_t)
                    {
                        if (t==initial_t)
                            continue;
                        get_h1_psnr(h1[predictor][t],psnr[predictor][t],AB_map,t,layer_eb,stat_eb);
                        dist[predictor][t]=-layer_default_slope*h1[predictor][t]+psnr[predictor][t];
                        if (dist[predictor][t]>dist[predictor][best_t[predictor]])
                            best_t[predictor]=t;
                    }
                }
                // 用最好的t实际压缩得到br和psnr
                vector<qb_t> qb_vec;
                block_loc={{0,data_shape[0]},{0,data_shape[1]},{0,data_shape[2]}};
                if (predictor.substr(0,6)=="cubic0")
                {
                    pivot_stride[0]*=2;
                    if (predictor=="cubic0_120")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0],pivot_stride[1]*generate_config_sample_stride,pivot_stride[2]*generate_config_sample_stride};
                        block_sample_compress_cubic0_120(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic0_021")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*generate_config_sample_stride,pivot_stride[1],pivot_stride[2]*generate_config_sample_stride};
                        block_sample_compress_cubic0_021(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic0_012")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*generate_config_sample_stride,pivot_stride[1]*generate_config_sample_stride,pivot_stride[2]};
                        block_sample_compress_cubic0_012(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    pivot_stride[0]/=2;
                }
                else if (predictor.substr(0,6)=="cubic1")
                {
                    pivot_stride[1]*=2;
                    if (predictor=="cubic1_120")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0],pivot_stride[1]*generate_config_sample_stride,pivot_stride[2]*generate_config_sample_stride};
                        block_sample_compress_cubic1_120(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic1_021")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*generate_config_sample_stride,pivot_stride[1],pivot_stride[2]*generate_config_sample_stride};
                        block_sample_compress_cubic1_021(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic1_012")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*generate_config_sample_stride,pivot_stride[1]*generate_config_sample_stride,pivot_stride[2]};
                        block_sample_compress_cubic1_012(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    pivot_stride[1]/=2;
                }
                else if (predictor.substr(0,6)=="cubic2")
                {
                    pivot_stride[2]*=2;
                    if (predictor=="cubic2_120")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0],pivot_stride[1]*generate_config_sample_stride,pivot_stride[2]*generate_config_sample_stride};
                        block_sample_compress_cubic2_120(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic2_021")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*generate_config_sample_stride,pivot_stride[1],pivot_stride[2]*generate_config_sample_stride};
                        block_sample_compress_cubic2_021(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    else if (predictor=="cubic2_012")
                    {
                        vector<uint64_t> temp_stride={pivot_stride[0]*generate_config_sample_stride,pivot_stride[1]*generate_config_sample_stride,pivot_stride[2]};
                        block_sample_compress_cubic2_012(qb_vec,qb_mse[predictor],block_loc,temp_stride,pivot_stride,best_t[predictor],layer_eb,neg_2_layer_eb);
                    }
                    pivot_stride[2]/=2;
                }
                //////// lossless compress qb ////////
                if (!qb_vec.empty())
                {
                    vector<unsigned char> huffman_bs_vec(data.size()*sizeof(float)*2);
                    unsigned char *huffman_bs=huffman_bs_vec.data();
                    huffman_encoder_class<qb_t> huffman_encoder;
                    huffman_encoder.preprocess_encode(qb_vec.data(),qb_vec.size());
                    huffman_encoder.save(huffman_bs);
                    huffman_encoder.encode(qb_vec.data(),qb_vec.size(),huffman_bs);
                    uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
                    uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
                    vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
                    uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
                    zstd_bs_vec.resize(zstd_bs_len);
                    T cr=(T)qb_vec.size()*sizeof(float)/zstd_bs_len;
                    qb_br[predictor]=8*sizeof(float)/cr;
                    qb_mse[predictor]=qb_mse[predictor]/qb_vec.size();
                    qb_psnr[predictor]=10*log10((max_val-min_val)*(max_val-min_val)/qb_mse[predictor]);
                    qb_num[predictor]=qb_vec.size();
                }
            }
            string best_layer_predictor="";
            T best_dist=-1e8;
            for (auto &qb_predictor:layer_candidate_predictors)
            {
                if (qb_num[qb_predictor]==0)
                    continue;
                if (best_layer_predictor.empty() || -layer_default_slope*qb_br[qb_predictor]+qb_psnr[qb_predictor]>best_dist)
                {
                    best_dist=-layer_default_slope*qb_br[qb_predictor]+qb_psnr[qb_predictor];
                    best_layer_predictor=qb_predictor;
                }
            }
            printf("best_layer_predictor=%s, best_dist=%f\n",best_layer_predictor.c_str(),best_dist);
            if (best_layer_predictor.empty())
                break;
            if (best_layer_predictor.substr(0,6)=="cubic0")
                pivot_stride[0]*=2;
            else if (best_layer_predictor.substr(0,6)=="cubic1")
                pivot_stride[1]*=2;
            else if (best_layer_predictor.substr(0,6)=="cubic2")
                pivot_stride[2]*=2;
            predictor_vec.insert(predictor_vec.begin(),best_layer_predictor);
        }
        generate_pivot_stride_and_block_shape_and_block_num();
        
        auto end_time=chrono::high_resolution_clock::now();
        printf("Generate config time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    }
}
