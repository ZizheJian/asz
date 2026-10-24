#pragma once

namespace asz
{
    namespace predictor_family_detail
    {
        using point_t=array<uint64_t,3>;

        struct result_c
        {
            uint64_t point_count=0;
            long double prediction_mse=0,reconstruction_mse=0,reconstruction_psnr=0,h1=0;
        };

        template<typename T>
        void copy_settings(param_c<T> &local,const param_c<T> &probe)
        {
            local.min_val=probe.min_val;
            local.max_val=probe.max_val;
            local.rel_eb=probe.rel_eb;
            local.abs_eb=probe.abs_eb;
            local.pivot_eb_ratio=probe.pivot_eb_ratio;
            local.eb_ratio=probe.eb_ratio;
            local.slope_ratio=probe.slope_ratio;
            local.default_slope=probe.default_slope;
            local.predictor_vec=probe.predictor_vec;
            local.pivot_stride=probe.pivot_stride;
            local.block_shape=probe.block_shape;
            local.block_pivot_ratio=probe.block_pivot_ratio;
            local.t_precision=probe.t_precision;
            local.t_min=probe.t_min;
            local.t_max=probe.t_max;
            local.block_t_policy=probe.block_t_policy;
            local.insufficient_sample_t=probe.insufficient_sample_t;
            local.quintic_fallback_t_policy=probe.quintic_fallback_t_policy;
            local.quintic_fallback_t=probe.quintic_fallback_t;
            local.stat_eb_ratio=probe.stat_eb_ratio;
            local.set_t_policy(probe.t_policy);
        }

        template<typename T>
        point_t copy_local_context(param_c<T> &local,const param_c<T> &probe,const vector<T> &source,const point_t &context_begin,const point_t &context_end)
        {
            point_t halo_begin;
            for(int axis=0;axis<3;axis++)
            {
                uint64_t left_halo=5*(probe.pivot_stride[axis]/2);
                halo_begin[axis]=context_begin[axis]>left_halo?context_begin[axis]-left_halo:0;
            }
            local.data_shape={context_end[0]-halo_begin[0],context_end[1]-halo_begin[1],context_end[2]-halo_begin[2]};
            local.data.resize(local.data_shape[0]*local.data_shape[1]*local.data_shape[2]);
            for(uint64_t i0=halo_begin[0];i0<context_end[0];i0++)
            for(uint64_t i1=halo_begin[1];i1<context_end[1];i1++)
            {
                uint64_t source_pos=(i0*probe.data_shape[1]+i1)*probe.data_shape[2]+halo_begin[2];
                uint64_t local_pos=((i0-halo_begin[0])*local.data_shape[1]+i1-halo_begin[1])*local.data_shape[2];
                copy(source.begin()+source_pos,source.begin()+source_pos+local.data_shape[2],local.data.begin()+local_pos);
            }
            local.compressed_data=local.data;
            copy_settings(local,probe);
            return halo_begin;
        }

        inline vector<point_t> make_stratified_targets(const vector<uint64_t> &block_num,uint64_t sample_count)
        {
            uint64_t total=block_num[0]*block_num[1]*block_num[2];
            sample_count=min(sample_count,total);
            mt19937_64 random_generator(0);
            vector<point_t> targets;
            for(uint64_t sample=0;sample<sample_count;sample++)
            {
                uint64_t segment_begin=(uint64_t)((unsigned __int128)sample*total/sample_count);
                uint64_t segment_end=(uint64_t)((unsigned __int128)(sample+1)*total/sample_count);
                uint64_t index=segment_begin+random_generator()%(segment_end-segment_begin);
                point_t target;
                target[2]=index%block_num[2];
                index/=block_num[2];
                target[1]=index%block_num[1];
                target[0]=index/block_num[1];
                targets.push_back(target);
            }
            return targets;
        }

        template<typename T>
        uint64_t sampled_block_point_count(const param_c<T> &probe,const point_t &target)
        {
            uint64_t count=1;
            for(uint64_t axis=0;axis<3;axis++)
            {
                uint64_t begin=target[axis]*probe.block_shape[axis];
                uint64_t end=min((target[axis]+1)*probe.block_shape[axis]+1,probe.data_shape[axis]);
                count*=end-begin;
            }
            return count;
        }

        template<typename T>
        vector<point_t> apply_point_budget(const param_c<T> &probe,const vector<point_t> &candidates,uint64_t point_budget,uint64_t &sampled_points)
        {
            vector<point_t> targets;
            sampled_points=0;
            for(const point_t &candidate:candidates)
            {
                uint64_t points=sampled_block_point_count(probe,candidate);
                if(sampled_points<=point_budget&&points<=point_budget-sampled_points)
                {
                    targets.push_back(candidate);
                    sampled_points+=points;
                }
            }
            return targets;
        }

        inline long double entropy(const vector<qb_t> &qbs)
        {
            if(qbs.empty())
                return 0;
            unordered_map<qb_t,uint64_t> frequencies;
            for(qb_t qb:qbs)
                frequencies[qb]++;
            long double h1=0;
            for(const auto &[qb,count]:frequencies)
            {
                long double probability=(long double)count/qbs.size();
                h1-=probability*log2(probability);
            }
            return h1;
        }

        template<typename T>
        result_c evaluate(const param_c<T> &probe,const vector<T> &source,const vector<point_t> &target_blocks,bool quintic)
        {
            uint64_t layer_num=probe.predictor_vec.size();
            T seed_eb=probe.abs_eb*probe.pivot_eb_ratio;
            vector<vector<qb_t>> layer_qbs(layer_num);
            vector<qb_t> context_qbs;
            vector<long double> prediction_sse(layer_num),reconstruction_sse(layer_num);
            vector<uint64_t> layer_counts(layer_num);
            for(const point_t &target_block:target_blocks)
            {
                point_t context_block_begin,target_block_end,context_begin,context_end;
                for(int axis=0;axis<3;axis++)
                {
                    context_block_begin[axis]=target_block[axis]?target_block[axis]-1:0;
                    target_block_end[axis]=target_block[axis]+1;
                    context_begin[axis]=context_block_begin[axis]*probe.block_shape[axis];
                    context_end[axis]=min(target_block_end[axis]*probe.block_shape[axis]+1,probe.data_shape[axis]);
                }
                param_c<T> local;
                point_t halo_begin=copy_local_context(local,probe,source,context_begin,context_end);
                local.force_quintic=quintic;
                local.layer_diagnostics.enabled=true;
                local.layer_diagnostics.reset(layer_num);
                for(uint64_t i0=context_begin[0];i0<context_end[0];i0+=probe.pivot_stride[0])
                for(uint64_t i1=context_begin[1];i1<context_end[1];i1+=probe.pivot_stride[1])
                for(uint64_t i2=context_begin[2];i2<context_end[2];i2+=probe.pivot_stride[2])
                {
                    uint64_t pos=((i0-halo_begin[0])*local.data_shape[1]+i1-halo_begin[1])*local.data_shape[2]+i2-halo_begin[2];
                    qb_t qb=(qb_t)llround((double)local.data[pos]/(2*(double)seed_eb));
                    local.compressed_data[pos]=(T)((double)qb*2*(double)seed_eb);
                }
                for(uint64_t block_i0=context_block_begin[0];block_i0<target_block_end[0];block_i0++)
                for(uint64_t block_i1=context_block_begin[1];block_i1<target_block_end[1];block_i1++)
                for(uint64_t block_i2=context_block_begin[2];block_i2<target_block_end[2];block_i2++)
                {
                    bool target=block_i0==target_block[0]&&block_i1==target_block[1]&&block_i2==target_block[2];
                    vector<vector<uint64_t>> block_loc(3);
                    block_loc[0]={block_i0*probe.block_shape[0]-halo_begin[0],min((block_i0+1)*probe.block_shape[0]+1,probe.data_shape[0])-halo_begin[0]};
                    block_loc[1]={block_i1*probe.block_shape[1]-halo_begin[1],min((block_i1+1)*probe.block_shape[1]+1,probe.data_shape[1])-halo_begin[1]};
                    block_loc[2]={block_i2*probe.block_shape[2]-halo_begin[2],min((block_i2+1)*probe.block_shape[2]+1,probe.data_shape[2])-halo_begin[2]};
                    auto stride=probe.pivot_stride;
                    for(uint64_t layer_id=0;layer_id<layer_num;layer_id++)
                    {
                        const string &predictor=probe.predictor_vec[layer_id];
                        T layer_eb=probe.abs_eb*pow(probe.eb_ratio,(int64_t)layer_num-(int64_t)layer_id-1);
                        T layer_slope=probe.default_slope*pow(probe.slope_ratio,(int64_t)layer_num-(int64_t)layer_id-1);
                        bool used_fallback=false;
                        bool fixed_quintic=quintic&&local.quintic_fallback_t_policy=="fixed";
                        T best_t=fixed_quintic?local.quintic_fallback_t:local.select_block_coefficient(predictor,block_loc,stride,layer_eb,layer_slope,used_fallback);
                        vector<qb_t> &qbs=target?layer_qbs[layer_id]:context_qbs;
                        if(!target)
                            context_qbs.clear();
                        local.layer_diagnostics.enabled=target;
                        local.layer_diagnostics.current_layer=layer_id;
                        unsigned char direction=predictor[5]-'0';
                        unsigned char order=predictor[9]-'0';
                        local.block_compress(qbs,block_loc,stride,best_t,layer_eb,direction,order);
                        stride[direction]/=2;
                    }
                }
                for(uint64_t layer_id=0;layer_id<layer_num;layer_id++)
                {
                    prediction_sse[layer_id]+=local.layer_diagnostics.prediction_squared_error[layer_id];
                    reconstruction_sse[layer_id]+=local.layer_diagnostics.reconstruction_squared_error[layer_id];
                    layer_counts[layer_id]+=local.layer_diagnostics.count[layer_id];
                }
            }
            result_c result;
            long double weighted_h1=0,prediction_total=0,reconstruction_total=0;
            for(uint64_t layer_id=0;layer_id<layer_num;layer_id++)
            {
                if(layer_counts[layer_id]!=layer_qbs[layer_id].size())
                    throw runtime_error("predictor-family target count mismatch");
                result.point_count+=layer_counts[layer_id];
                prediction_total+=prediction_sse[layer_id];
                reconstruction_total+=reconstruction_sse[layer_id];
                weighted_h1+=entropy(layer_qbs[layer_id])*layer_counts[layer_id];
            }
            if(result.point_count==0)
                throw runtime_error("predictor-family sample contains no target points");
            result.prediction_mse=prediction_total/result.point_count;
            result.reconstruction_mse=reconstruction_total/result.point_count;
            long double value_range=(long double)probe.max_val-probe.min_val;
            result.reconstruction_psnr=result.reconstruction_mse==0?INFINITY:10*log10(value_range*value_range/result.reconstruction_mse);
            result.h1=weighted_h1/result.point_count;
            return result;
        }
    }

    template<typename T>
    void param_c<T>::select_predictor_family()
    {
        auto start_time=chrono::high_resolution_clock::now();
        if(predictor_vec.empty())
            throw runtime_error("cannot select predictor family without a predictor plan");
        param_c<T> probe;
        predictor_family_detail::copy_settings(probe,*this);
        probe.data_shape=data_shape;
        uint64_t suffix_layers=min(predictor_family_suffix_layers,(uint64_t)predictor_vec.size());
        probe.predictor_vec.assign(predictor_vec.end()-suffix_layers,predictor_vec.end());
        probe.block_pivot_ratio=rel_eb<=predictor_family_fine_eb_threshold?predictor_family_fine_probe_block_pivot_ratio:predictor_family_coarse_probe_block_pivot_ratio;
        probe.generate_pivot_stride_and_block_shape_and_block_num();
        auto candidates=predictor_family_detail::make_stratified_targets(probe.block_num,predictor_family_sample_blocks);
        uint64_t fraction_budget=(uint64_t)floor((long double)data.size()*predictor_family_sample_fraction_limit);
        uint64_t point_budget=min(predictor_family_sample_point_limit,fraction_budget);
        uint64_t sampled_points=0;
        auto targets=predictor_family_detail::apply_point_budget(probe,candidates,point_budget,sampled_points);
        if(targets.empty())
        {
            force_quintic=false;
            printf("Predictor family selection: selector=h1, suffix_layers=%lu, blocks=0, sampled_block_points=0, sample_point_budget=%lu, probe_block_pivot_ratio=%lu, fallback=point_budget, family=cubic\n",suffix_layers,point_budget,probe.block_pivot_ratio);
        }
        else
        {
            auto cubic=predictor_family_detail::evaluate(probe,data,targets,false);
            auto quintic=predictor_family_detail::evaluate(probe,data,targets,true);
            long double psnr_gain=isinf(quintic.reconstruction_psnr)&&quintic.reconstruction_psnr==cubic.reconstruction_psnr?0:quintic.reconstruction_psnr-cubic.reconstruction_psnr;
            long double score_gain=psnr_gain-(long double)default_slope*(quintic.h1-cubic.h1);
            force_quintic=score_gain>0;
            printf("Predictor family selection: selector=h1, suffix_layers=%lu, blocks=%lu, sampled_block_points=%lu, sample_point_budget=%lu, probe_block_pivot_ratio=%lu, points=%lu, cubic_mse=%.12Le, quintic_mse=%.12Le, cubic_psnr=%.12Le, quintic_psnr=%.12Le, cubic_h1=%.12Le, quintic_h1=%.12Le, six_score_gain=%.12Le, family=%s\n",suffix_layers,(uint64_t)targets.size(),sampled_points,point_budget,probe.block_pivot_ratio,cubic.point_count,cubic.prediction_mse,quintic.prediction_mse,cubic.reconstruction_psnr,quintic.reconstruction_psnr,cubic.h1,quintic.h1,score_gain,force_quintic?"quintic":"cubic");
        }
        auto end_time=chrono::high_resolution_clock::now();
        printf("Predictor family selection time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    }
}
