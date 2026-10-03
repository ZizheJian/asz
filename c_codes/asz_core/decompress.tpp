#pragma once

namespace asz
{
    template<typename T>
    void param_c<T>::dot_decompress(vector<qb_t> &qb_vec,uint64_t &qb_pos,uint64_t i,uint64_t half_stride,uint64_t right,uint64_t pos,uint64_t dist,T t,T eb,uint64_t qb_index)
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
        uint64_t current_qb_pos=qb_index==numeric_limits<uint64_t>::max()?qb_pos:qb_index;
        compressed_data[pos]=(T)((double)pred-(double)qb_vec[current_qb_pos]*2*(double)eb);
        if (qb_index==numeric_limits<uint64_t>::max())
            qb_pos++;
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic0_120(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb)
    {
        array<uint64_t,3> target_block_loc;
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
    void param_c<T>::block_decompress_cubic0_021(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb)
    {
        array<uint64_t,3> target_block_loc;
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
    void param_c<T>::block_decompress_cubic0_012(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char qb_order)
    {
        array<uint64_t,3> target_block_loc;
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
        uint64_t qb_num=get_layer_qb_num(qb_shape);
        if (qb_pos>qb_vec.size() || qb_num>qb_vec.size()-qb_pos)
            throw runtime_error("compressed stream has too few QBs");
        uint64_t qb_base=qb_pos;
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        for (uint64_t i0=target_block_loc[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
        for (uint64_t i1=target_block_loc[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
        for (uint64_t i2=target_block_loc[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
            dot_decompress(qb_vec,qb_pos,i0,stride[0]/2,block_loc[0][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[0]*data_shape[1]*data_shape[2]/2,t,eb,qb_index);
        qb_pos+=qb_num;
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic1_120(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb)
    {
        array<uint64_t,3> target_block_left;
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
    void param_c<T>::block_decompress_cubic1_021(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb)
    {
        array<uint64_t,3> target_block_left;
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
    void param_c<T>::block_decompress_cubic1_012(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char qb_order)
    {
        array<uint64_t,3> target_block_left;
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
        uint64_t qb_num=get_layer_qb_num(qb_shape);
        if (qb_pos>qb_vec.size() || qb_num>qb_vec.size()-qb_pos)
            throw runtime_error("compressed stream has too few QBs");
        uint64_t qb_base=qb_pos;
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        for (uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
        for (uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
        for (uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
            dot_decompress(qb_vec,qb_pos,i1,stride[1]/2,block_loc[1][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[1]*data_shape[2]/2,t,eb,qb_index);
        qb_pos+=qb_num;
    }

    template<typename T>
    void param_c<T>::block_decompress_cubic2_120(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb)
    {
        array<uint64_t,3> target_block_left;
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
    void param_c<T>::block_decompress_cubic2_021(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb)
    {
        array<uint64_t,3> target_block_left;
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
    void param_c<T>::block_decompress_cubic2_012(vector<qb_t> &qb_vec,uint64_t &qb_pos,array<array<uint64_t,2>,3> &block_loc,array<uint64_t,3> &stride,T t,T eb,unsigned char qb_order)
    {
        array<uint64_t,3> target_block_left;
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
        uint64_t qb_num=get_layer_qb_num(qb_shape);
        if (qb_pos>qb_vec.size() || qb_num>qb_vec.size()-qb_pos)
            throw runtime_error("compressed stream has too few QBs");
        uint64_t qb_base=qb_pos;
        uint64_t qb_inner_stride=qb_order==0?qb_shape[0]:qb_order==1?qb_shape[1]:1;
        for (uint64_t i0=target_block_left[0],j0=0;i0<block_loc[0][1];i0+=stride[0],j0++)
        for (uint64_t i1=target_block_left[1],j1=0;i1<block_loc[1][1];i1+=stride[1],j1++)
        for (uint64_t i2=target_block_left[2],qb_index=qb_base+get_qb_index(j0,j1,0,qb_shape,qb_order);i2<block_loc[2][1];i2+=stride[2],qb_index+=qb_inner_stride)
            dot_decompress(qb_vec,qb_pos,i2,stride[2]/2,block_loc[2][1],i0*data_shape[1]*data_shape[2]+i1*data_shape[2]+i2,stride[2]/2,t,eb,qb_index);
        qb_pos+=qb_num;
    }

    template<typename T>
    void param_c<T>::decompress()
    {
        auto start_time=chrono::high_resolution_clock::now();

        uint64_t huffman_bs_len=ZSTD_getFrameContentSize(zstd_bs_vec.data(),zstd_bs_vec.size());
        vector<unsigned char> huffman_bs_vec(huffman_bs_len);
        if (ZSTD_decompress(huffman_bs_vec.data(),huffman_bs_len,zstd_bs_vec.data(),zstd_bs_vec.size())!=huffman_bs_len)
            throw runtime_error("ZSTD_decompress error in decompress()");
        auto zstd_end_time=chrono::high_resolution_clock::now();
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
        predictor_vec.clear();
        for (uint64_t i=0;i<layer_num;i++)
        {
            if (huffman_bs[0]<'0'||huffman_bs[0]>'2'||huffman_bs[1]<'0'||huffman_bs[1]>'2')
                throw runtime_error("compressed stream contains an invalid predictor");
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
            huffman_encoder_class<qb_t> huffman_encoder;
            huffman_encoder.load(huffman_bs);
            huffman_encoder.decode(huffman_bs,qb_vec_vec[i].data(),len);
        }
        auto huffman_end_time=chrono::high_resolution_clock::now();
        generate_pivot_stride_and_block_shape_and_block_num();
        uint64_t t_pos=0;
        vector<uint64_t> qb_pos_vec(qb_vec_vec.size(),0);
        compressed_data.resize(data_shape[0]*data_shape[1]*data_shape[2]);
        abs_eb=rel_eb*(max_val-min_val);
        vector<unsigned char> predictor_direction(layer_num),predictor_order(layer_num);
        vector<T> layer_eb_vec(layer_num);
        for (uint64_t layer_id=0;layer_id<layer_num;layer_id++)
        {
            predictor_direction[layer_id]=predictor_vec[layer_id][5]-'0';
            predictor_order[layer_id]=predictor_vec[layer_id][9]-'0';
            layer_eb_vec[layer_id]=abs_eb*pow(eb_ratio,layer_num-layer_id-1);
        }
        auto setup_end_time=chrono::high_resolution_clock::now();
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
            array<array<uint64_t,2>,3> block_loc={{{block_i0*block_shape[0],min((block_i0+1)*block_shape[0]+1,data_shape[0])},{block_i1*block_shape[1],min((block_i1+1)*block_shape[1]+1,data_shape[1])},{block_i2*block_shape[2],min((block_i2+1)*block_shape[2]+1,data_shape[2])}}};
            array<uint64_t,3> stride={pivot_stride[0],pivot_stride[1],pivot_stride[2]};
            //////// 逐层解压 ////////
            for (uint32_t layer_id=0;layer_id<layer_num;layer_id++)
            {
                //////// 获取最好t2 ////////
                if (t_int_vec.empty())
                    throw runtime_error("compressed stream contains no t value");
                T best_t=(T)t_int_vec[t_int_vec.size()==1?0:t_pos]/t_precision;
                if (t_int_vec.size()!=1)
                    t_pos++;
                //////// 预测 ////////
                unsigned char direction=predictor_direction[layer_id];
                unsigned char order=predictor_order[layer_id];
                if (direction>2 || order>2)
                    throw runtime_error("compressed stream contains an invalid predictor");
                vector<qb_t> &layer_qbs=qb_vec_vec[layer_id+1];
                uint64_t &layer_qb_pos=qb_pos_vec[layer_id+1];
                if (predictor_direction[layer_id]==0)
                {
                    block_decompress_cubic0_012(layer_qbs,layer_qb_pos,block_loc,stride,best_t,layer_eb_vec[layer_id],order);
                }
                else if (predictor_direction[layer_id]==1)
                {
                    block_decompress_cubic1_012(layer_qbs,layer_qb_pos,block_loc,stride,best_t,layer_eb_vec[layer_id],order);
                }
                else if (predictor_direction[layer_id]==2)
                {
                    block_decompress_cubic2_012(layer_qbs,layer_qb_pos,block_loc,stride,best_t,layer_eb_vec[layer_id],order);
                }
                else
                    throw runtime_error("unsupported predictor direction");
                stride[direction]/=2;
            }
        }
        auto end_time=chrono::high_resolution_clock::now();
        printf("Zstd decompression time: %f s\n",chrono::duration<double>(zstd_end_time-start_time).count());
        printf("Huffman decompression time: %f s\n",chrono::duration<double>(huffman_end_time-zstd_end_time).count());
        printf("Reconstruction setup time: %f s\n",chrono::duration<double>(setup_end_time-huffman_end_time).count());
        printf("Prediction reconstruction time: %f s\n",chrono::duration<double>(end_time-setup_end_time).count());
        printf("Decompression time: %f s\n",chrono::duration<double>(end_time-start_time).count());
        
        T cr=(T)compressed_data.size()*sizeof(float)/zstd_bs_vec.size();
        T br=8*sizeof(float)/cr;
        printf("CR= %f\n",cr);
        printf("BR= %f\n",br);
    }
}
