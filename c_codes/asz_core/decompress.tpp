#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::dot_decompress(vector<int64_t> &qb_vec,uint64_t &qb_pos,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb)
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
        compressed_data[pos]=(T)((double)pred-(double)qb_vec[qb_pos]*2*(double)eb);
        qb_pos++;
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic0_120(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic0_021(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic0_012(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic1_120(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic1_021(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic1_012(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic2_120(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic2_021(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic2_012(vector<int64_t> &qb_vec,uint64_t &qb_pos,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T t,T eb)
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
            dot_decompress(qb_vec,qb_pos,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb);
    }

    template<typename T>
    void param_c<T>::decompress()
    {
        auto start_time=chrono::high_resolution_clock::now();

        uint64_t huffman_bs_len=ZSTD_getFrameContentSize(zstd_bs_vec.data(),zstd_bs_vec.size());
        vector<unsigned char> huffman_bs_vec(huffman_bs_len);
        if (ZSTD_decompress(huffman_bs_vec.data(),huffman_bs_len,zstd_bs_vec.data(),zstd_bs_vec.size())!=huffman_bs_len)
            throw runtime_error("ZSTD_decompress error in decompress()");
        const unsigned char *huffman_bs=huffman_bs_vec.data();
        memcpy(&min_val,huffman_bs,sizeof(T));
        huffman_bs+=sizeof(T);
        memcpy(&max_val,huffman_bs,sizeof(T));
        huffman_bs+=sizeof(T);
        unsigned char format_and_layer_num=huffman_bs[0];
        uint64_t layer_num;
        if (format_and_layer_num&0x40)
        {
            force_quintic=format_and_layer_num&0x80;
            layer_num=format_and_layer_num&0x3F;
        }
        else
            layer_num=format_and_layer_num;
        huffman_bs++;
        for (uint64_t i=0;i<layer_num;i++)
        {
            string predictor="cubic";
            predictor+=huffman_bs[0];
            predictor+="_";
            if (huffman_bs[1]=='0')
                predictor+="120";
            else if (huffman_bs[1]=='1')
                predictor+="021";
            else if (huffman_bs[1]=='2')
                predictor+="012";
            huffman_bs+=2;
            predictor_vec.push_back(predictor);
        }
        {
            uint64_t len=0;
            for (int i=0;i<8;i++)
                len|=((uint64_t)huffman_bs[i])<<(i*8);
            huffman_bs+=8;
            t_int_vec.resize(len);
            huffman_encoder_class<int64_t> huffman_t_int_encoder;
            huffman_t_int_encoder.load(huffman_bs);
            huffman_t_int_encoder.decode(huffman_bs,t_int_vec.data(),len);
        }
        qb_vec_vec.resize(layer_num+1);
        for (uint64_t i=0;i<layer_num+1;i++)
        {
            uint64_t len=0;
            for (int j=0;j<8;j++)
                len|=((uint64_t)huffman_bs[j])<<(j*8);
            huffman_bs+=8;
            qb_vec_vec[i].resize(len);
            if (len==0)
                continue;
            huffman_encoder_class<int64_t> huffman_encoder;
            huffman_encoder.load(huffman_bs);
            huffman_encoder.decode(huffman_bs,qb_vec_vec[i].data(),0);
        }
        generate_pivot_stride_and_block_shape_and_block_num();
        uint64_t t_pos=0;
        vector<uint64_t> qb_pos_vec(qb_vec_vec.size(),0);
        compressed_data.resize(data_shape[0]*data_shape[1]*data_shape[2]);
        abs_eb=rel_eb*(max_val-min_val);
        //////// 读取原始数据 ////////
        ifstream data_file(original_data_path,ios::binary);
        if (sizeof(T)==sizeof(float))
        {
            data.resize(data_shape[0]*data_shape[1]*data_shape[2]);
            data_file.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(float));
        }
        else
        {
            vector<float> float_data(data_shape[0]*data_shape[1]*data_shape[2]);
            data_file.read(reinterpret_cast<char*>(float_data.data()),float_data.size()*sizeof(float));
            data.resize(data_shape[0]*data_shape[1]*data_shape[2]);
            data.assign(float_data.begin(),float_data.end());
        }
        data_file.close();
        //////// 解压pivot points ////////
        uint64_t pivot_num=(data_shape[0]+pivot_stride[0]-1)/pivot_stride[0];
        pivot_num*=((data_shape[1]+pivot_stride[1]-1)/pivot_stride[1]);
        pivot_num*=((data_shape[2]+pivot_stride[2]-1)/pivot_stride[2]);
        T pivot_eb=abs_eb*pivot_eb_ratio;
        for (uint64_t i0=0;i0<data_shape[0];i0+=pivot_stride[0])
        for (uint64_t i1=0;i1<data_shape[1];i1+=pivot_stride[1])
        for (uint64_t i2=0;i2<data_shape[2];i2+=pivot_stride[2])
        {
            uint64_t pos=i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2;
            compressed_data[pos]=(T)((double)qb_vec_vec[0][qb_pos_vec[0]]*(double)pivot_eb*2);
            qb_pos_vec[0]++;
        }
        // //////// 依次处理每个大block ////////
        for (uint64_t block_i0=0;block_i0<block_num[0];block_i0++)
        for (uint64_t block_i1=0;block_i1<block_num[1];block_i1++)
        for (uint64_t block_i2=0;block_i2<block_num[2];block_i2++)
        {
            vector<vector<uint64_t>> block_loc(3);
            block_loc[0]={block_i0*block_shape[0],min((block_i0+1)*block_shape[0]+1,data_shape[0])};
            block_loc[1]={block_i1*block_shape[1],min((block_i1+1)*block_shape[1]+1,data_shape[1])};
            block_loc[2]={block_i2*block_shape[2],min((block_i2+1)*block_shape[2]+1,data_shape[2])};
            auto stride=pivot_stride;
            //////// 逐层解压 ////////
            uint32_t layer_num=predictor_vec.size();
            for (uint32_t layer_id=0;layer_id<layer_num;layer_id++)
            {
                string predictor=predictor_vec[layer_id];
                T layer_eb=abs_eb*pow(eb_ratio,layer_num-layer_id-1);
                //////// 获取最好t2 ////////
                T best_t=(T)t_int_vec[t_pos]/t_precision;
                t_pos++;
                //////// 预测 ////////
                if (predictor.substr(0,6)=="cubic0")
                {
                    if (predictor=="cubic0_120")
                        block_decompress_cubic0_120(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    else if (predictor=="cubic0_021")
                        block_decompress_cubic0_021(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    else if (predictor=="cubic0_012")
                        block_decompress_cubic0_012(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    stride[0]/=2;
                }
                else if (predictor.substr(0,6)=="cubic1")
                {
                    if (predictor=="cubic1_120")
                        block_decompress_cubic1_120(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    else if (predictor=="cubic1_021")
                        block_decompress_cubic1_021(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    else if (predictor=="cubic1_012")
                        block_decompress_cubic1_012(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    stride[1]/=2;
                }
                else if (predictor.substr(0,6)=="cubic2")
                {
                    if (predictor=="cubic2_120")
                        block_decompress_cubic2_120(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    else if (predictor=="cubic2_021")
                        block_decompress_cubic2_021(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    else if (predictor=="cubic2_012")
                        block_decompress_cubic2_012(qb_vec_vec[layer_id+1],qb_pos_vec[layer_id+1],block_loc,stride,best_t,layer_eb);
                    stride[2]/=2;
                }
            }
        }
        auto end_time=chrono::high_resolution_clock::now();
        printf("Decompression time: %f s\n",chrono::duration<double>(end_time-start_time).count());
        
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
        printf("CR= %f\n",cr);
        printf("BR= %f\n",br);
        printf("PSNR= %f\n",psnr);
    }
}
