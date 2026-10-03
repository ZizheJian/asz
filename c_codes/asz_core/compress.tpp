#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::dot_compress(vector<qb_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,T neg_2_eb,uint64_t qb_pos)
    {
        T pred;
        if (force_quintic&&i>=5*half_stride&&i+5*half_stride<right)
        {
            pred=(T)((75.0/128)*(compressed_data[pos-dist]+compressed_data[pos+dist])-(25.0/256)*(compressed_data[pos-3*dist]+compressed_data[pos+3*dist])+(3.0/256)*(compressed_data[pos-5*dist]+compressed_data[pos+5*dist]));
        }
        else if (i<=half_stride)
        {
            if (i+half_stride>=right)
                pred=compressed_data[pos-dist];
            else if (i+3*half_stride>=right)
                pred=(compressed_data[pos-dist]+compressed_data[pos+dist])/2;
            else
                pred=(3*compressed_data[pos-dist]+6*compressed_data[pos+dist]-compressed_data[pos+3*dist])/8;
        }
        else
        {
            if (i+half_stride>=right)
                pred=(-compressed_data[pos-3*dist]+3*compressed_data[pos-dist])/2;
            else if (i+3*half_stride>=right)
                pred=(-compressed_data[pos-3*dist]+6*compressed_data[pos-dist]+3*compressed_data[pos+dist])/8;
            else 
            {
                pred=(0.25-t)*(compressed_data[pos-3*dist]+compressed_data[pos+3*dist]);
                pred+=(0.25+t)*(compressed_data[pos-dist]+compressed_data[pos+dist]);
            }
        }
        qb_t qb=(qb_t)llround(((double)pred-(double)data[pos])/(2*(double)eb));
        if (qb_pos==numeric_limits<uint64_t>::max())
            qb_vec.push_back(qb);
        else
            qb_vec[qb_pos]=qb;
        compressed_data[pos]=(T)((double)pred-(double)qb*2*(double)eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic0_120(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
        for (uint64_t i1=target_block_loc[1];i1<block_loc[1][1];i1+=stride[1])
        for (uint64_t i2=target_block_loc[2];i2<block_loc[2][1];i2+=stride[2])
        for (uint64_t i0=target_block_loc[0];i0<block_loc[0][1];i0+=stride[0])
            dot_compress(qb_vec,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic0_021(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
        for (uint64_t i0=target_block_loc[0];i0<block_loc[0][1];i0+=stride[0])
        for (uint64_t i2=target_block_loc[2];i2<block_loc[2][1];i2+=stride[2])
        for (uint64_t i1=target_block_loc[1];i1<block_loc[1][1];i1+=stride[1])
            dot_compress(qb_vec,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic0_012(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb,unsigned char qb_order)
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
        auto qb_shape=get_layer_qb_shape(block_loc,stride,0);
        uint64_t qb_base=qb_vec.size();
        qb_vec.resize(qb_base+get_layer_qb_num(qb_shape));
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        for (uint64_t i0=target_block_loc[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
        for (uint64_t i1=target_block_loc[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
        for (uint64_t i2=target_block_loc[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
            dot_compress(qb_vec,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb,qb_index);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic1_120(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=stride[2])
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=stride[0])
            dot_compress(qb_vec,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic1_021(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=stride[0])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=stride[2])
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=stride[1])
            dot_compress(qb_vec,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic1_012(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb,unsigned char qb_order)
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
        auto qb_shape=get_layer_qb_shape(block_loc,stride,1);
        uint64_t qb_base=qb_vec.size();
        qb_vec.resize(qb_base+get_layer_qb_num(qb_shape));
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        for (uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
        for (uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
        for (uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
            dot_compress(qb_vec,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,neg_2_eb,qb_index);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic2_120(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=stride[2])
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=stride[0])
            dot_compress(qb_vec,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic2_021(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb)
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
        for (uint64_t i0=target_block_left[0];i0<block_loc[0][1];i0+=stride[0])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=stride[2])
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=stride[1])
            dot_compress(qb_vec,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb);
    }

    template<typename T>
    void param_c<T>::block_compress_cubic2_012(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,T neg_2_eb,unsigned char qb_order)
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
        auto qb_shape=get_layer_qb_shape(block_loc,stride,2);
        uint64_t qb_base=qb_vec.size();
        qb_vec.resize(qb_base+get_layer_qb_num(qb_shape));
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        for (uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
        for (uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
        for (uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
            dot_compress(qb_vec,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb,qb_index);
    }

    template<typename T>
    T param_c<T>::compress()
    {
        printf("min_val=%f max_val=%f\n",min_val,max_val);
        auto start_time=chrono::high_resolution_clock::now();
        compressed_data=data;
        for (auto &qb_vec:qb_vec_vec)
            qb_vec.clear();
        qb_vec_vec.resize(predictor_vec.size()+1);
        for (uint64_t i=0;i<qb_vec_vec.size();i++)
            qb_vec_vec[i].reserve((uint64_t)(data.size()*pow(2,(int64_t)i-(int64_t)qb_vec_vec.size()+1)));
        t_int_vec.clear();
        uint64_t t_fallback_count=0;
        if (t_policy!="adaptive")
            t_int_vec.push_back(llround(candidate_t.front()*t_precision));

        //////// 存储pivot points ////////
        uint64_t pivot_num=(data_shape[0]+pivot_stride[0]-1)/pivot_stride[0];
        pivot_num*=((data_shape[1]+pivot_stride[1]-1)/pivot_stride[1]);
        pivot_num*=((data_shape[2]+pivot_stride[2]-1)/pivot_stride[2]);
        qb_vec_vec[0].reserve(pivot_num);
        T pivot_eb=abs_eb*pivot_eb_ratio;
        for (uint64_t i0=0;i0<data_shape[0];i0+=pivot_stride[0])
        for (uint64_t i1=0;i1<data_shape[1];i1+=pivot_stride[1])
        for (uint64_t i2=0;i2<data_shape[2];i2+=pivot_stride[2])
        {
            uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
            qb_t qb=(qb_t)llround((double)data[pos]/(2*(double)pivot_eb));
            qb_vec_vec[0].push_back(qb);
            compressed_data[pos]=(T)((double)qb*(double)pivot_eb*2);
        }
        //////// 依次处理每个大block ////////
        for (uint64_t block_i0=0;block_i0<block_num[0];block_i0++)
        for (uint64_t block_i1=0;block_i1<block_num[1];block_i1++)
        for (uint64_t block_i2=0;block_i2<block_num[2];block_i2++)
        {
            vector<vector<uint64_t>> block_loc(3);
            block_loc[0]={block_i0*block_shape[0],min((block_i0+1)*block_shape[0]+1,data_shape[0])};
            block_loc[1]={block_i1*block_shape[1],min((block_i1+1)*block_shape[1]+1,data_shape[1])};
            block_loc[2]={block_i2*block_shape[2],min((block_i2+1)*block_shape[2]+1,data_shape[2])};
            auto stride=pivot_stride;
            //////// 逐层压缩 ////////
            uint32_t layer_num=predictor_vec.size();
            for (uint32_t layer_id=0;layer_id<layer_num;layer_id++)
            {
                string predictor=predictor_vec[layer_id];
                T layer_eb=abs_eb*pow(eb_ratio,layer_num-layer_id-1);
                T neg_2_layer_eb=1/(2*layer_eb);
                T layer_default_slope=default_slope*pow(slope_ratio,(int32_t)layer_num-(int32_t)layer_id-1);
                //////// 估计最好t2 ////////
                T stat_eb=layer_eb*stat_eb_ratio;
                T neg_2_stat_eb=1/(2*stat_eb);
                unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
                if (t_policy=="adaptive" && (predictor.substr(0,6)=="cubic0") && (block_loc[0][1]>block_loc[0][0]+3*stride[0]))
                {
                    vector<vector<uint64_t>> temp_block_loc(3);
                    temp_block_loc[0]={block_loc[0][0]+3*stride[0]/2,block_loc[0][1]-3*stride[0]/2};
                    temp_block_loc[1]={block_loc[1][0],block_loc[1][1]};
                    temp_block_loc[2]={block_loc[2][0],block_loc[2][1]};
                    get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb);
                }
                else if (t_policy=="adaptive" && (predictor.substr(0,6)=="cubic1") && (block_loc[1][1]>block_loc[1][0]+3*stride[1]))
                {
                    vector<vector<uint64_t>> temp_block_loc(3);
                    temp_block_loc[0]={block_loc[0][0],block_loc[0][1]};
                    temp_block_loc[1]={block_loc[1][0]+3*stride[1]/2,block_loc[1][1]-3*stride[1]/2};
                    temp_block_loc[2]={block_loc[2][0],block_loc[2][1]};
                    get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[1]*data_shape[2]/2,neg_2_stat_eb);
                }
                else if (t_policy=="adaptive" && (predictor.substr(0,6)=="cubic2") && (block_loc[2][1]>block_loc[2][0]+3*stride[2]))
                {
                    vector<vector<uint64_t>> temp_block_loc(3);
                    temp_block_loc[0]={block_loc[0][0],block_loc[0][1]};
                    temp_block_loc[1]={block_loc[1][0],block_loc[1][1]};
                    temp_block_loc[2]={block_loc[2][0]+3*stride[2]/2,block_loc[2][1]-3*stride[2]/2};
                    get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[2]/2,neg_2_stat_eb);
                }
                T best_t=t_policy=="adaptive"?(T)4/16:candidate_t.front(),best_h1=0,best_psnr=0;
                if (!AB_map.empty())
                {
                    get_h1_psnr(best_h1,best_psnr,AB_map,best_t,layer_eb,stat_eb);
                    for (auto t:candidate_t)
                    {
                        if (t==best_t || best_psnr==INFINITY)
                            continue;
                        T h1=0,psnr=0;
                        get_h1_psnr(h1,psnr,AB_map,t,layer_eb,stat_eb);
                        if (psnr==INFINITY || -layer_default_slope*(h1-best_h1)+(psnr-best_psnr)>0)
                        {
                            best_t=t;
                            best_h1=h1;
                            best_psnr=psnr;
                        }
                    }
                }
                else if (t_policy=="adaptive")
                    t_fallback_count++;
                if (t_policy=="adaptive")
                    t_int_vec.push_back(llround(best_t*t_precision));
                //////// 预测 ////////
                unsigned char direction=predictor[5]-'0';
                unsigned char order=predictor[9]-'0';
                vector<qb_t> &layer_qbs=qb_vec_vec[layer_id+1];
                if (predictor.substr(0,6)=="cubic0")
                {
                    block_compress_cubic0_012(layer_qbs,block_loc,stride,best_t,layer_eb,neg_2_layer_eb,order);
                }
                else if (predictor.substr(0,6)=="cubic1")
                {
                    block_compress_cubic1_012(layer_qbs,block_loc,stride,best_t,layer_eb,neg_2_layer_eb,order);
                }
                else if (predictor.substr(0,6)=="cubic2")
                {
                    block_compress_cubic2_012(layer_qbs,block_loc,stride,best_t,layer_eb,neg_2_layer_eb,order);
                }
                else
                    throw runtime_error("unsupported predictor direction");
                stride[direction]/=2;
            }
        }
        uint64_t total_qb_num=0;
        for (auto &qb_vec:qb_vec_vec)
            total_qb_num+=qb_vec.size();
        printf("total_qb_num=%lu\n",total_qb_num);
        printf("t_int_vec.size()=%lu\n",t_int_vec.size());
        if (report_t_histogram)
        {
            map<int64_t,uint64_t> t_histogram;
            for (auto t_int:t_int_vec)
                t_histogram[t_int]++;
            printf("T histogram:");
            bool first=true;
            for (const auto &[t_int,count]:t_histogram)
            {
                printf("%s%lld=%lu",first?"":",",(long long)t_int,count);
                first=false;
            }
            printf("\n");
            printf("T fallback count:%lu\n",t_fallback_count);
        }
        if (total_qb_num!=data.size())
            throw runtime_error("total_qb_num!=data.size()");
        //////// 编码 ////////
        vector<unsigned char> huffman_bs_vec(data.size()*sizeof(float)*2);
        unsigned char *huffman_bs=huffman_bs_vec.data();
        memcpy(huffman_bs,&min_val,sizeof(T));
        huffman_bs+=sizeof(T);
        memcpy(huffman_bs,&max_val,sizeof(T));
        huffman_bs+=sizeof(T);
        huffman_bs[0]=static_cast<unsigned char>(predictor_vec.size())|0x40|(force_quintic?0x80:0);
        huffman_bs++;
        for (auto &predictor:predictor_vec)
        {
            huffman_bs[0]=predictor[5];
            huffman_bs[1]=predictor[9];
            huffman_bs+=2;
        }
        {
            uint64_t len=t_int_vec.size();
            for (int i=0;i<8;i++)
                huffman_bs[i]=(len>>(i*8))&0xFF;
            huffman_bs+=8;
            if (!t_int_vec.empty())
            {
                huffman_encoder_class<int64_t> huffman_t_int_encoder;
                huffman_t_int_encoder.preprocess_encode(t_int_vec.data(),t_int_vec.size());
                huffman_t_int_encoder.save(huffman_bs);
                huffman_t_int_encoder.encode(t_int_vec.data(),t_int_vec.size(),huffman_bs);
            }
        }
        for (uint64_t i=0;i<qb_vec_vec.size();i++)
        {   
            uint64_t len=qb_vec_vec[i].size();
            for (int j=0;j<8;j++)
                huffman_bs[j]=(len>>(j*8))&0xFF;
            huffman_bs+=8;
            if (qb_vec_vec[i].empty())
                continue;
            huffman_encoder_class<qb_t> huffman_encoder;
            huffman_encoder.preprocess_encode(qb_vec_vec[i].data(),qb_vec_vec[i].size());
            huffman_encoder.save(huffman_bs);
            huffman_encoder.encode(qb_vec_vec[i].data(),qb_vec_vec[i].size(),huffman_bs);
        }

        uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
        uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
        zstd_bs_vec.resize(max_zstd_bs_len);
        unsigned char *zstd_bs=zstd_bs_vec.data();
        zstd_bs+=ZSTD_compress(zstd_bs,max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
        zstd_bs_vec.resize(zstd_bs-zstd_bs_vec.data());
        auto end_time=chrono::high_resolution_clock::now();
        printf("Compression time: %f s\n",chrono::duration<double>(end_time-start_time).count());

        T cr=(T)data.size()*sizeof(float)/zstd_bs_vec.size();
        T br=8*sizeof(float)/cr;
        T mse=0,max_err=0;
        for (uint64_t i=0;i<data.size();i++)
        {
            mse+=(data[i]-compressed_data[i])*(data[i]-compressed_data[i]);
            max_err=max(max_err,abs(data[i]-compressed_data[i]));
        }
        mse/=data.size();
        T psnr=10*log10((max_val-min_val)*(max_val-min_val)/mse);
        printf("max_err= %f (%f%%)\n",max_err,max_err*100/abs_eb);
        printf("CR: %f, BR: %f, PSNR: %f\n",cr,br,psnr);
        printf("dist=%f\n",-default_slope*br+psnr);
        return -default_slope*br+psnr;
    }
}
