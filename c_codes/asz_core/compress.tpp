#pragma once

namespace asz
{
    void param_c::dot_compress(vector<int64_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,float t,float eb,float neg_2_eb)
    {
        float pred;
        if (i<=half_stride)
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
        int64_t qb=llround((pred-compressed_data[pos])*neg_2_eb);
        qb_vec.push_back(qb);
        compressed_data[pos]=pred-qb*2*eb;
    }

    void param_c::block_compress_cubic0_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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

    void param_c::block_compress_cubic0_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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

    void param_c::block_compress_cubic0_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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
        for (uint64_t i1=target_block_loc[1];i1<block_loc[1][1];i1+=stride[1])
        for (uint64_t i2=target_block_loc[2];i2<block_loc[2][1];i2+=stride[2])
            dot_compress(qb_vec,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_compress_cubic1_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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

    void param_c::block_compress_cubic1_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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

    void param_c::block_compress_cubic1_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=stride[2])
            dot_compress(qb_vec,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,neg_2_eb);
    }

    void param_c::block_compress_cubic2_120(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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

    void param_c::block_compress_cubic2_021(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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

    void param_c::block_compress_cubic2_012(vector<int64_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float t,float eb,float neg_2_eb)
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
        for (uint64_t i1=target_block_left[1];i1<block_loc[1][1];i1+=stride[1])
        for (uint64_t i2=target_block_left[2];i2<block_loc[2][1];i2+=stride[2])
            dot_compress(qb_vec,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,neg_2_eb);
    }

    float param_c::compress()
    {
        compressed_data=data;
        for (auto &qb_vec:qb_vec_vec)
            qb_vec.clear();
        qb_vec_vec.resize(predictor_vec.size()+1);
        for (uint64_t i=0;i<qb_vec_vec.size();i++)
            qb_vec_vec[i].reserve((uint64_t)(data.size()*pow(2,i-qb_vec_vec.size()+1)));
        t_int_vec.clear();
        //////// 存储pivot points ////////
        uint64_t pivot_num=(data_shape[0]+pivot_stride[0]-1)/pivot_stride[0];
        pivot_num*=((data_shape[1]+pivot_stride[1]-1)/pivot_stride[1]);
        pivot_num*=((data_shape[2]+pivot_stride[2]-1)/pivot_stride[2]);
        qb_vec_vec[0].reserve(pivot_num);
        float pivot_eb=abs_eb*pivot_eb_ratio;
        float neg_2_pivot_eb=1/(2*pivot_eb);
        for (uint64_t i0=0;i0<data_shape[0];i0+=pivot_stride[0])
            for (uint64_t i1=0;i1<data_shape[1];i1+=pivot_stride[1])
                for (uint64_t i2=0;i2<data_shape[2];i2+=pivot_stride[2])
                {
                    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                    int64_t qb=llround(data[pos]*neg_2_pivot_eb);
                    qb_vec_vec[0].push_back(qb);
                    compressed_data[pos]=qb*pivot_eb*2;
                }
        //////// 依次处理每个大block ////////
        for (uint64_t block_i0=0;block_i0<block_num[0];block_i0++)
            for (uint64_t block_i1=0;block_i1<block_num[1];block_i1++)
                for (uint64_t block_i2=0;block_i2<block_num[2];block_i2++)
                {
                    uint64_t block_id=block_i0*block_num[1]*block_num[2]+block_i1*block_num[2]+block_i2;
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
                        float layer_eb=abs_eb*pow(eb_ratio,layer_num-layer_id-1);
                        float neg_2_layer_eb=1/(2*layer_eb);
                        //////// 估计最好t2 ////////
                        float stat_eb=layer_eb*stat_eb_ratio;
                        float neg_2_stat_eb=1/(2*stat_eb);
                        unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
                        if ((predictor.compare(0,6,"cubic0")==0) && (block_loc[0][1]>block_loc[0][0]+3*stride[0]))
                        {
                            vector<vector<uint64_t>> temp_block_loc(3);
                            temp_block_loc[0]={block_loc[0][0]+3*stride[0]/2,block_loc[0][1]-3*stride[0]/2};
                            temp_block_loc[1]={block_loc[1][0],block_loc[1][1]};
                            temp_block_loc[2]={block_loc[2][0],block_loc[2][1]};
                            get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb);
                        }
                        else if ((predictor=="cubic1") && (block_loc[1][1]>block_loc[1][0]+3*stride[1]))
                        {
                            vector<vector<uint64_t>> temp_block_loc(3);
                            temp_block_loc[0]={block_loc[0][0],block_loc[0][1]};
                            temp_block_loc[1]={block_loc[1][0]+3*stride[1]/2,block_loc[1][1]-3*stride[1]/2};
                            temp_block_loc[2]={block_loc[2][0],block_loc[2][1]};
                            get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[1]*data_shape[2]/2,neg_2_stat_eb);
                        }
                        else if ((predictor=="cubic2") && (block_loc[2][1]>block_loc[2][0]+3*stride[2]))
                        {
                            vector<vector<uint64_t>> temp_block_loc(3);
                            temp_block_loc[0]={block_loc[0][0],block_loc[0][1]};
                            temp_block_loc[1]={block_loc[1][0],block_loc[1][1]};
                            temp_block_loc[2]={block_loc[2][0]+3*stride[2]/2,block_loc[2][1]-3*stride[2]/2};
                            get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[2]/2,neg_2_stat_eb);
                        }
                        float best_t,best_h1,best_psnr;
                        if (AB_map.empty())
                        {
                            best_t=0.3125;
                            best_h1=0;
                            best_psnr=0;
                        }
                        else
                        {
                            float h1=0,psnr=0;
                            bool any_t_tried=false;
                            for (auto t:candidate_t)
                            {
                                get_h1_psnr(h1,psnr,AB_map,t,layer_eb,stat_eb);
                                if ((!any_t_tried) || (-default_slope*pow(slope_ratio,layer_num-layer_id+1)*(h1-best_h1)+(psnr-best_psnr)>0))
                                {
                                    best_t=t;
                                    best_h1=h1;
                                    best_psnr=psnr;
                                }
                            }
                        }
                        t_int_vec.push_back(llround(best_t*t_precision));
                        //////// 预测 ////////
                        if (predictor.compare(0,6,"cubic0")==0)
                        {
                            if (predictor=="cubic0_120")
                                block_compress_cubic0_120(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            else if (predictor=="cubic0_021")
                                block_compress_cubic0_021(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            else if (predictor=="cubic0_012")
                                block_compress_cubic0_012(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            stride[0]/=2;
                        }
                        else if (predictor.compare(0,6,"cubic1")==0)
                        {
                            if (predictor=="cubic1_120")
                                block_compress_cubic1_120(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            else if (predictor=="cubic1_021")
                                block_compress_cubic1_021(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            else if (predictor=="cubic1_012")
                                block_compress_cubic1_012(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            stride[1]/=2;
                        }
                        else if (predictor.compare(0,6,"cubic2")==0)
                        {
                            if (predictor=="cubic2_120")
                                block_compress_cubic2_120(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            else if (predictor=="cubic2_021")
                                block_compress_cubic2_021(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            else if (predictor=="cubic2_012")
                                block_compress_cubic2_012(qb_vec_vec[layer_id+1],block_loc,stride,best_t,layer_eb,neg_2_layer_eb);
                            stride[2]/=2;
                        }
                    }
                }
        uint64_t total_qb_num=0;
        for (auto &qb_vec:qb_vec_vec)
            total_qb_num+=qb_vec.size();
        printf("total_qb_num=%lu\n",total_qb_num);
        printf("t_int_vec.size()=%lu\n",t_int_vec.size());
        if (total_qb_num!=data.size())
            throw runtime_error("total_qb_num!=data.size()");
        //////// 编码 ////////
        vector<unsigned char> huffman_bs_vec(data.size()*sizeof(float)*2);
        unsigned char *huffman_bs=huffman_bs_vec.data();
        for (uint64_t i=0;i<qb_vec_vec.size();i++)
        {   
            if (qb_vec_vec[i].empty())
                continue;
            huffman_encoder_class<int64_t> huffman_encoder;
            huffman_encoder.preprocess_encode(qb_vec_vec[i].data(),qb_vec_vec[i].size());
            huffman_encoder.save(huffman_bs);
            huffman_encoder.encode(qb_vec_vec[i].data(),qb_vec_vec[i].size(),huffman_bs);
        }
        if (!t_int_vec.empty())
        {
            huffman_encoder_class<int64_t> huffman_t_int_encoder;
            huffman_t_int_encoder.preprocess_encode(t_int_vec.data(),t_int_vec.size());
            huffman_t_int_encoder.save(huffman_bs);
            huffman_t_int_encoder.encode(t_int_vec.data(),t_int_vec.size(),huffman_bs);
        }

        uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
        uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
        vector<unsigned char> zstd_bs_vec(max_zstd_bs_len);
        uint64_t zstd_bs_len=ZSTD_compress(zstd_bs_vec.data(),max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
        zstd_bs_vec.resize(zstd_bs_len);
        float cr=(float)data.size()*sizeof(float)/zstd_bs_len;
        float br=8*sizeof(float)/cr;
        float mse=0;
        for (uint64_t i=0;i<data.size();i++)
            mse+=(data[i]-compressed_data[i])*(data[i]-compressed_data[i]);
        mse/=data.size();
        float psnr=10*log10((max_val-min_val)*(max_val-min_val)/mse);
        printf("CR: %f, BR: %f, PSNR: %f\n",cr,br,psnr);
        printf("dist=%f\n",-default_slope*br+psnr);
        return -default_slope*br+psnr;
    }
}