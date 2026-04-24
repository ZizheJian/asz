#pragma once

namespace asz
{
    void param_c::dot_compress(vector<int64_t> &temp_qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,float t2,
        float neg_2_layer_eb,float layer_eb)
    {
        if (data_compressed[pos])
            return;
        float pred;
        if (i<=half_stride)
        {
            if (i+half_stride>=right)
            {
                assert(data_compressed[pos-half_stride*dist]);
                pred=compressed_data[pos-half_stride*dist];
            }
            else if (i+3*half_stride>=right)
            {
                assert(data_compressed[pos-half_stride*dist]);
                assert(data_compressed[pos+half_stride*dist]);
                pred=(compressed_data[pos-half_stride*dist]+compressed_data[pos+half_stride*dist])/2;
            }
            else
            {
                assert(data_compressed[pos-half_stride*dist]);
                assert(data_compressed[pos+half_stride*dist]);
                assert(data_compressed[pos+3*half_stride*dist]);
                pred=(3*compressed_data[pos-half_stride*dist]+6*compressed_data[pos+half_stride*dist]-compressed_data[pos+3*half_stride*dist])/8;
            }
        }
        else
        {
            if (i+half_stride>=right)
            {
                assert(data_compressed[pos-3*half_stride*dist]);
                assert(data_compressed[pos-half_stride*dist]);
                pred=(-compressed_data[pos-3*half_stride*dist]+3*compressed_data[pos-half_stride*dist])/2;
            }
            else if (i+3*half_stride>=right)
            {
                assert(data_compressed[pos-3*half_stride*dist]);
                assert(data_compressed[pos-half_stride*dist]);
                assert(data_compressed[pos+half_stride*dist]);
                pred=(-compressed_data[pos-3*half_stride*dist]+6*compressed_data[pos-half_stride*dist]+3*compressed_data[pos+half_stride*dist])/8;
            }
            else 
            {
                assert(data_compressed[pos-3*half_stride*dist]);
                assert(data_compressed[pos-half_stride*dist]);
                assert(data_compressed[pos+half_stride*dist]);
                assert(data_compressed[pos+3*half_stride*dist]);
                pred=(0.25-t2)*(compressed_data[pos-3*half_stride*dist]+compressed_data[pos+3*half_stride*dist]);
                pred+=(0.25+t2)*(compressed_data[pos-half_stride*dist]+compressed_data[pos+half_stride*dist]);
            }
        }
        int64_t qb=llround((pred-compressed_data[pos])*neg_2_layer_eb);
        temp_qb_vec.push_back(qb);
        compressed_data[pos]=pred-qb*2*layer_eb;
        data_compressed[pos]=true;
    }

    void param_c::block_compress_cubic1(vector<int64_t> &temp_qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float best_t2,float layer_eb,
        float neg_2_layer_eb)
    {
        for (uint64_t i1=block_loc[1][0];i1<block_loc[1][1];i1+=stride[1])
            for (uint64_t i2=block_loc[2][0];i2<block_loc[2][1];i2+=stride[2])
                for (uint64_t i0=block_loc[0][0]+stride[0]/2;i0<block_loc[0][1];i0+=stride[0])
                    dot_compress(temp_qb_vec,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,data_shape[1]*data_shape[2],
                        best_t2,neg_2_layer_eb,layer_eb);
    }

    void param_c::block_compress_cubic2(vector<int64_t> &temp_qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float best_t2,float layer_eb,
        float neg_2_layer_eb)
    {
        for (uint64_t i0=block_loc[0][0];i0<block_loc[0][1];i0+=stride[0])
            for (uint64_t i2=block_loc[2][0];i2<block_loc[2][1];i2+=stride[2])
                for (uint64_t i1=block_loc[1][0]+stride[1]/2;i1<block_loc[1][1];i1+=stride[1])
                    dot_compress(temp_qb_vec,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,data_shape[2],
                        best_t2,neg_2_layer_eb,layer_eb);
    }

    void param_c::block_compress_cubic3(vector<int64_t> &temp_qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,float best_t2,float layer_eb,
        float neg_2_layer_eb)
    {
        for (uint64_t i0=block_loc[0][0];i0<block_loc[0][1];i0+=stride[0])
            for (uint64_t i1=block_loc[1][0];i1<block_loc[1][1];i1+=stride[1])
                for (uint64_t i2=block_loc[2][0]+stride[2]/2;i2<block_loc[2][1];i2+=stride[2])
                    dot_compress(temp_qb_vec,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,1,
                        best_t2,neg_2_layer_eb,layer_eb);
    }

    float param_c::compress()
    {
        compressed_data=data;
        data_compressed.assign(data.size(),0);
        qb_vec.clear();
        t2_int_vec.clear();
        //////// 存储pivot points ////////
        vector<int64_t> pivot_qb;
        uint64_t pivot_num=(data_shape[0]+pivot_stride[0]-1)/pivot_stride[0];
        pivot_num*=((data_shape[1]+pivot_stride[1]-1)/pivot_stride[1]);
        pivot_num*=((data_shape[2]+pivot_stride[2]-1)/pivot_stride[2]);
        pivot_qb.reserve(pivot_num);
        float pivot_eb=abs_eb*pivot_eb_ratio;
        float neg_2_pivot_eb=1/(2*pivot_eb);
        for (uint64_t i0=0;i0<data_shape[0];i0+=pivot_stride[0])
            for (uint64_t i1=0;i1<data_shape[1];i1+=pivot_stride[1])
                for (uint64_t i2=0;i2<data_shape[2];i2+=pivot_stride[2])
                {
                    uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
                    int64_t qb=llround(data[pos]*neg_2_pivot_eb);
                    pivot_qb.push_back(qb);
                    compressed_data[pos]=qb*pivot_eb*2;
                    data_compressed[pos]=true;
                }
        qb_vec.push_back(pivot_qb);
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
                    auto block_predictor_vec=predictor_vec[block_id];
                    auto block_eb_ratio_vec=eb_ratio_vec[block_id];
                    auto stride=pivot_stride;
                    //////// 逐层压缩 ////////
                    uint32_t layer_num=block_predictor_vec.size();
                    qb_vec.push_back(vector<int64_t>());
                    for (uint32_t layer_id=0;layer_id<layer_num;layer_id++)
                    {
                        string predictor=block_predictor_vec[layer_id];
                        float layer_eb=abs_eb;
                        for (uint32_t i=layer_id;i<layer_num;i++)
                            layer_eb*=block_eb_ratio_vec[i];
                        float neg_2_layer_eb=1/(2*layer_eb);
                        //////// 估计最好t2 ////////
                        float stat_eb=layer_eb*0.01;
                        float neg_2_stat_eb=1/(2*stat_eb);
                        unordered_map<tuple<int64_t,int64_t>,uint64_t> AB_map;
                        if (predictor=="cubic1")
                        {
                            if (block_loc[0][1]>block_loc[0][0]+3*stride[0])
                            {
                                vector<vector<uint64_t>> temp_block_loc(3);
                                temp_block_loc[0]={block_loc[0][0]+3*stride[0]/2,block_loc[0][1]-3*stride[0]/2};
                                temp_block_loc[1]={block_loc[1][0],block_loc[1][1]};
                                temp_block_loc[2]={block_loc[2][0],block_loc[2][1]};
                                get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[0]*data_shape[1]*data_shape[2]/2,neg_2_stat_eb);
                            }
                        }
                        else if (predictor=="cubic2")
                        {
                            if (block_loc[1][1]>block_loc[1][0]+3*stride[1])
                            {
                                vector<vector<uint64_t>> temp_block_loc(3);
                                temp_block_loc[0]={block_loc[0][0],block_loc[0][1]};
                                temp_block_loc[1]={block_loc[1][0]+3*stride[1]/2,block_loc[1][1]-3*stride[1]/2};
                                temp_block_loc[2]={block_loc[2][0],block_loc[2][1]};
                                get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[1]*data_shape[2]/2,neg_2_stat_eb);
                            }
                        }
                        else if (predictor=="cubic3")
                        {
                            if (block_loc[2][1]>block_loc[2][0]+3*stride[2])
                            {
                                vector<vector<uint64_t>> temp_block_loc(3);
                                temp_block_loc[0]={block_loc[0][0],block_loc[0][1]};
                                temp_block_loc[1]={block_loc[1][0],block_loc[1][1]};
                                temp_block_loc[2]={block_loc[2][0]+3*stride[2]/2,block_loc[2][1]-3*stride[2]/2};
                                get_AB_map(AB_map,compressed_data,temp_block_loc,stride,stride[2]/2,neg_2_stat_eb);
                            }
                        }
                        uint64_t AB_num=0;
                        for (const auto &[AB_key,count]:AB_map)
                            AB_num+=count;
                        float best_t2=0,best_br=0,best_psnr=0;
                        if (AB_map.empty())
                        {
                            best_t2=0.3125;
                            best_br=-1;
                            best_psnr=-1;
                        }
                        else
                        {
                            float br=0,psnr=0;
                            for (auto t2:possible_t2_vec)
                            {
                                estimate_br_psnr(br,psnr,AB_map,t2,layer_eb,stat_eb,AB_num);
                                if ((t2==possible_t2_vec[0]) || (-default_slope*(br-best_br)+(psnr-best_psnr)>0))
                                {
                                    best_t2=t2;
                                    best_br=br;
                                    best_psnr=psnr;
                                }
                            }
                        }
                        // printf("best_t2=%f,best_br=%f,best_psnr=%f\n",best_t2,best_br,best_psnr);
                        t2_int_vec.push_back(llround(best_t2*t2_precision));
                        //////// 量化 ////////
                        if (predictor=="cubic1")
                        {
                            block_compress_cubic1(qb_vec.back(),block_loc,stride,best_t2,layer_eb,neg_2_layer_eb);
                            stride[0]/=2;
                        }
                        else if (predictor=="cubic2")
                        {
                            block_compress_cubic2(qb_vec.back(),block_loc,stride,best_t2,layer_eb,neg_2_layer_eb);
                            stride[1]/=2;
                        }
                        else if (predictor=="cubic3")
                        {
                            block_compress_cubic3(qb_vec.back(),block_loc,stride,best_t2,layer_eb,neg_2_layer_eb);
                            stride[2]/=2;
                        }
                    }
                }
        assert(all_of(data_compressed.begin(),data_compressed.end(),[](bool v){return v;}));
        uint64_t qb_vec_len=0;
        for (auto &block_qb_vec:qb_vec)
            qb_vec_len+=block_qb_vec.size();
        assert(qb_vec_len==data.size());
        //////// 编码 ////////
        qb_vec.push_back(t2_int_vec);
        vector<unsigned char> huffman_bs_vec(data.size()*sizeof(float)*2);
        unsigned char *huffman_bs=huffman_bs_vec.data();

        // for (auto &block_qb_vec:qb_vec)
        // {
        //     huffman_encoder_class<int64_t> huffman_encoder;
        //     huffman_encoder.preprocess_encode(block_qb_vec.data(),block_qb_vec.size());
        //     huffman_encoder.save(huffman_bs);
        //     huffman_encoder.encode(block_qb_vec.data(),block_qb_vec.size(),huffman_bs);
        // }

        vector<int64_t> concatenated_qb_vec;
        for (auto &block_qb_vec:qb_vec)
            concatenated_qb_vec.insert(concatenated_qb_vec.end(),block_qb_vec.begin(),block_qb_vec.end());
        // printf("concatenated_qb_vec size=%lu\n",concatenated_qb_vec.size());
        huffman_encoder_class<int64_t> huffman_encoder;
        huffman_encoder.preprocess_encode(concatenated_qb_vec.data(),concatenated_qb_vec.size());
        huffman_encoder.save(huffman_bs);
        huffman_encoder.encode(concatenated_qb_vec.data(),concatenated_qb_vec.size(),huffman_bs);

        uint64_t huffman_bs_len=huffman_bs-huffman_bs_vec.data();
        // printf("huffman_bs_len=%lu\n",huffman_bs_len);
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