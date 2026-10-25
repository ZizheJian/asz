#pragma once

namespace asz
{
    template<typename T>
    template<bool diagnostics>
    void param_c<T>::dot_compress(vector<qb_t> &qb_vec,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,uint64_t qb_pos)
    {
        T pred;
        if(force_quintic&&i>=5*half_stride&&i+5*half_stride<right)
        {
            pred=(T)(one_d_six_quintic_inner*(compressed_data[pos-dist]+compressed_data[pos+dist])+one_d_six_quintic_b*(compressed_data[pos-3*dist]+compressed_data[pos+3*dist])+one_d_six_quintic_a*(compressed_data[pos-5*dist]+compressed_data[pos+5*dist]));
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
        qb_vec[qb_pos]=qb;
        compressed_data[pos]=(T)((double)pred-(double)qb*2*(double)eb);
        if constexpr(diagnostics)
            layer_diagnostics.record(pred,compressed_data[pos],data[pos]);
    }

    template<typename T>
    void param_c<T>::block_compress(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,unsigned char direction,unsigned char qb_order)
    {
        if(layer_diagnostics.enabled)
            block_compress_impl<true>(qb_vec,block_loc,stride,t,eb,direction,qb_order);
        else
            block_compress_impl<false>(qb_vec,block_loc,stride,t,eb,direction,qb_order);
    }

    template<typename T>
    template<bool diagnostics>
    void param_c<T>::block_compress_impl(vector<qb_t> &qb_vec,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb,unsigned char direction,unsigned char qb_order)
    {
        if(direction>2)
            throw runtime_error("unsupported predictor direction");
        array<uint64_t,3> target_block_left;
        for(uint64_t axis=0;axis<3;axis++)
            target_block_left[axis]=axis==direction?block_loc[axis][0]+stride[axis]/2:block_loc[axis][0]==0?0:block_loc[axis][0]+stride[axis];
        auto qb_shape=get_layer_qb_shape(block_loc,stride,direction);
        uint64_t qb_base=qb_vec.size();
        qb_vec.resize(qb_base+get_layer_qb_num(qb_shape));
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        uint64_t point_distance=stride[direction]/2;
        for(uint64_t axis=direction+1;axis<3;axis++)
            point_distance*=data_shape[axis];
        if(direction==0)
        {
            for(uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
            for(uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
            for(uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
                dot_compress<diagnostics>(qb_vec,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,point_distance,t,eb,qb_index);
        }
        else if(direction==1)
        {
            for(uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
            for(uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
            for(uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
                dot_compress<diagnostics>(qb_vec,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,point_distance,t,eb,qb_index);
        }
        else
        {
            for(uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
            for(uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
            for(uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
                dot_compress<diagnostics>(qb_vec,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,point_distance,t,eb,qb_index);
        }
    }

    template<typename T>
    T param_c<T>::select_block_coefficient(const string &predictor,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T layer_eb,T layer_default_slope,bool &used_fallback)
    {
        used_fallback=false;
        if(t_policy!="adaptive")
            return block_candidate_t.front();

        unsigned char direction=predictor[5]-'0';
        T best_t=insufficient_sample_t;
        if(direction>2||block_loc[direction][1]<=block_loc[direction][0]+3*stride[direction])
        {
            used_fallback=true;
            return best_t;
        }

        array<array<uint64_t,2>,3> sample_loc;
        array<uint64_t,3> sample_stride;
        for(uint64_t axis=0;axis<3;axis++)
        {
            sample_loc[axis]={block_loc[axis][0],block_loc[axis][1]};
            sample_stride[axis]=stride[axis];
        }
        sample_loc[direction][0]+=3*stride[direction]/2;
        sample_loc[direction][1]-=3*stride[direction]/2;
        uint64_t sample_distance=stride[direction]/2;
        for(uint64_t axis=direction+1;axis<3;axis++)
            sample_distance*=data_shape[axis];

        T stat_eb=layer_eb*stat_eb_ratio;
        unordered_map<tuple<int64_t,int64_t>,uint64_t> coefficient_statistics;
        get_AB_map(coefficient_statistics,compressed_data,sample_loc,sample_stride,sample_distance,1/(2*stat_eb));
        if(coefficient_statistics.empty())
        {
            used_fallback=true;
            return best_t;
        }

        T best_h1=0,best_psnr=0;
        get_h1_psnr(best_h1,best_psnr,coefficient_statistics,best_t,layer_eb,stat_eb);
        for(T candidate:block_candidate_t)
        {
            if(candidate==best_t||best_psnr==INFINITY)
                continue;
            T h1=0,psnr=0;
            get_h1_psnr(h1,psnr,coefficient_statistics,candidate,layer_eb,stat_eb);
            T score_improvement=-layer_default_slope*(h1-best_h1)+(psnr-best_psnr);
            if(psnr==INFINITY||score_improvement>0)
            {
                best_t=candidate;
                best_h1=h1;
                best_psnr=psnr;
            }
        }
        return best_t;
    }

    template<typename T>
    void param_c<T>::print_layer_diagnostics(const vector<uint64_t> &layer_huffman_bytes)
    {
        long double value_range=(long double)max_val-(long double)min_val;
        uint32_t layer_num=predictor_vec.size();
        for(uint32_t layer_id=0;layer_id<layer_num;layer_id++)
        {
            const vector<qb_t> &layer_qbs=qb_vec_vec[layer_id+1];
            uint64_t point_count=layer_diagnostics.count[layer_id];
            if(point_count!=layer_qbs.size())
                throw runtime_error("layer diagnostic count does not match quantization-bin count");
            if(point_count==0)
                continue;

            unordered_map<qb_t,uint64_t> frequencies;
            for(qb_t qb:layer_qbs)
                frequencies[qb]++;
            long double h1=0;
            uint64_t zero_count=0;
            for(const auto &[qb,count]:frequencies)
            {
                long double probability=(long double)count/point_count;
                h1-=probability*log2(probability);
                if(qb==0)
                    zero_count=count;
            }

            long double prediction_mse=layer_diagnostics.prediction_squared_error[layer_id]/point_count;
            long double prediction_mae=layer_diagnostics.prediction_absolute_error[layer_id]/point_count;
            long double reconstruction_mse=layer_diagnostics.reconstruction_squared_error[layer_id]/point_count;
            long double reconstruction_mae=layer_diagnostics.reconstruction_absolute_error[layer_id]/point_count;
            long double reconstruction_psnr=reconstruction_mse==0?INFINITY:10*log10(value_range*value_range/reconstruction_mse);
            long double layer_slope=default_slope*pow(slope_ratio,(int32_t)layer_num-(int32_t)layer_id-1);
            long double h1_psnr_score=reconstruction_psnr-layer_slope*h1;
            long double layer_eb=abs_eb*pow(eb_ratio,layer_num-layer_id-1);
            long double huffman_bps=(long double)8*layer_huffman_bytes[layer_id+1]/point_count;
            long double zero_fraction=(long double)zero_count/point_count;
            printf("Layer diagnostics: layer=%u, predictor=%s, points=%lu, eb=%.12Le, prediction_mse=%.12Le, prediction_mae=%.12Le, reconstruction_mse=%.12Le, reconstruction_mae=%.12Le, reconstruction_psnr=%.12Le, h1=%.12Le, zero_fraction=%.12Le, huffman_bytes=%lu, huffman_bps=%.12Le, slope=%.12Le, h1_psnr_score=%.12Le\n",layer_id,predictor_vec[layer_id].c_str(),point_count,layer_eb,prediction_mse,prediction_mae,reconstruction_mse,reconstruction_mae,reconstruction_psnr,h1,zero_fraction,layer_huffman_bytes[layer_id+1],huffman_bps,layer_slope,h1_psnr_score);
        }
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
        bool fixed_quintic_fallback=force_quintic&&quintic_fallback_t_policy=="fixed";
        if(t_policy!="adaptive"||fixed_quintic_fallback)
            t_int_vec.push_back(llround((fixed_quintic_fallback?quintic_fallback_t:block_candidate_t.front())*t_precision));
        uint32_t layer_num=predictor_vec.size();
        layer_diagnostics.reset(layer_num);

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
        vector<vector<uint64_t>> block_loc(3,vector<uint64_t>(2));
        vector<uint64_t> stride(3);
        for (uint64_t block_i0=0;block_i0<block_num[0];block_i0++)
        for (uint64_t block_i1=0;block_i1<block_num[1];block_i1++)
        for (uint64_t block_i2=0;block_i2<block_num[2];block_i2++)
        {
            block_loc[0][0]=block_i0*block_shape[0];
            block_loc[0][1]=min((block_i0+1)*block_shape[0]+1,data_shape[0]);
            block_loc[1][0]=block_i1*block_shape[1];
            block_loc[1][1]=min((block_i1+1)*block_shape[1]+1,data_shape[1]);
            block_loc[2][0]=block_i2*block_shape[2];
            block_loc[2][1]=min((block_i2+1)*block_shape[2]+1,data_shape[2]);
            stride=pivot_stride;
            //////// 逐层压缩 ////////
            for (uint32_t layer_id=0;layer_id<layer_num;layer_id++)
            {
                string predictor=predictor_vec[layer_id];
                T layer_eb=abs_eb*pow(eb_ratio,layer_num-layer_id-1);
                T layer_default_slope=default_slope*pow(slope_ratio,(int32_t)layer_num-(int32_t)layer_id-1);
                //////// 为当前block选择系数 ////////
                bool used_fallback=false;
                T best_t=fixed_quintic_fallback?quintic_fallback_t:select_block_coefficient(predictor,block_loc,stride,layer_eb,layer_default_slope,used_fallback);
                if(used_fallback)
                    t_fallback_count++;
                if(t_policy=="adaptive"&&!fixed_quintic_fallback)
                    t_int_vec.push_back(llround(best_t*t_precision));
                //////// 预测 ////////
                unsigned char direction=predictor[5]-'0';
                unsigned char order=predictor[9]-'0';
                vector<qb_t> &layer_qbs=qb_vec_vec[layer_id+1];
                layer_diagnostics.current_layer=layer_id;
                block_compress(layer_qbs,block_loc,stride,best_t,layer_eb,direction,order);
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
        auto huffman_start_time=chrono::high_resolution_clock::now();
        vector<unsigned char> huffman_bs_vec;
        auto append_huffman_bytes=[&huffman_bs_vec](uint64_t len)
        {
            if (len>numeric_limits<size_t>::max()-huffman_bs_vec.size())
                throw length_error("Huffman stream is too large");
            size_t offset=huffman_bs_vec.size();
            huffman_bs_vec.resize(offset+(size_t)len);
            return huffman_bs_vec.data()+offset;
        };
        unsigned char *huffman_bs=append_huffman_bytes(2*sizeof(T)+1+2*predictor_vec.size());
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
            huffman_bs=append_huffman_bytes(8);
            for (int i=0;i<8;i++)
                huffman_bs[i]=(len>>(i*8))&0xFF;
            if (!t_int_vec.empty())
            {
                huffman_encoder_class<int64_t> huffman_t_int_encoder;
                huffman_t_int_encoder.preprocess_encode(t_int_vec.data(),t_int_vec.size());
                uint64_t encoded_size=huffman_t_int_encoder.save_size()+huffman_t_int_encoder.encode_size();
                huffman_bs=append_huffman_bytes(encoded_size);
                unsigned char *huffman_end=huffman_bs+encoded_size;
                huffman_t_int_encoder.save(huffman_bs);
                huffman_t_int_encoder.encode(t_int_vec.data(),t_int_vec.size(),huffman_bs);
                if (huffman_bs!=huffman_end)
                    throw runtime_error("Huffman encoded size mismatch");
            }
        }
        vector<uint64_t> layer_huffman_bytes(layer_diagnostics.enabled?qb_vec_vec.size():0,0);
        for (uint64_t i=0;i<qb_vec_vec.size();i++)
        {   
            uint64_t len=qb_vec_vec[i].size();
            huffman_bs=append_huffman_bytes(8);
            for (int j=0;j<8;j++)
                huffman_bs[j]=(len>>(j*8))&0xFF;
            if (qb_vec_vec[i].empty())
                continue;
            huffman_encoder_class<qb_t> huffman_encoder;
            huffman_encoder.preprocess_encode(qb_vec_vec[i].data(),qb_vec_vec[i].size());
            uint64_t encoded_size=huffman_encoder.save_size()+huffman_encoder.encode_size();
            if (layer_diagnostics.enabled)
                layer_huffman_bytes[i]=encoded_size;
            huffman_bs=append_huffman_bytes(encoded_size);
            unsigned char *huffman_end=huffman_bs+encoded_size;
            huffman_encoder.save(huffman_bs);
            huffman_encoder.encode(qb_vec_vec[i].data(),qb_vec_vec[i].size(),huffman_bs);
            if (huffman_bs!=huffman_end)
                throw runtime_error("Huffman encoded size mismatch");
        }
        auto huffman_end_time=chrono::high_resolution_clock::now();

        uint64_t huffman_bs_len=huffman_bs_vec.size();
        uint64_t max_zstd_bs_len=ZSTD_compressBound(huffman_bs_len);
        zstd_bs_vec.resize(max_zstd_bs_len);
        unsigned char *zstd_bs=zstd_bs_vec.data();
        zstd_bs+=ZSTD_compress(zstd_bs,max_zstd_bs_len,huffman_bs_vec.data(),huffman_bs_len,3);
        zstd_bs_vec.resize(zstd_bs-zstd_bs_vec.data());
        auto end_time=chrono::high_resolution_clock::now();
        double core_compression_time=chrono::duration<double>(end_time-start_time).count();
        printf("Huffman compression time: %f s\n",chrono::duration<double>(huffman_end_time-huffman_start_time).count());
        printf("Zstd compression time: %f s\n",chrono::duration<double>(end_time-huffman_end_time).count());
        printf("Core compression time: %f s\n",core_compression_time);
        printf("Compression time: %f s\n",data_range_time+core_compression_time);

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
        if(layer_diagnostics.enabled)
            print_layer_diagnostics(layer_huffman_bytes);
        return -default_slope*br+psnr;
    }
}
