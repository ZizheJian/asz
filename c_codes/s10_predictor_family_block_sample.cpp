#include "asz_core/asz_param.hpp"

#include <array>
#include <chrono>
#include <iomanip>
#include <numeric>
#include <sstream>

using namespace std;

using point_t=array<uint64_t,3>;
using qb_t=asz::qb_t;

struct family_result_c
{
    string family,seed_mode;
    double seed_eb=0,initialization_seconds=0,simulation_seconds=0,statistics_seconds=0,lossless_seconds=0,total_seconds=0;
    uint64_t pivot_count=0,target_count=0,huffman_bytes=0,zstd_bytes=0;
    long double prediction_mse=0,prediction_mae=0,reconstruction_mse=0,reconstruction_mae=0,reconstruction_psnr=0,weighted_h1=0,zero_fraction=0,huffman_bps=0,zstd_bps=0;
    vector<uint64_t> layer_counts,layer_huffman_bytes;
    vector<long double> layer_prediction_mse,layer_prediction_mae,layer_reconstruction_mse,layer_reconstruction_mae,layer_reconstruction_psnr,layer_h1,layer_zero_fraction,layer_huffman_bps;
};

double elapsed_seconds(const chrono::steady_clock::time_point &begin)
{
    return chrono::duration<double>(chrono::steady_clock::now()-begin).count();
}

vector<string> parse_predictor_plan(const string &text)
{
    vector<string> predictors;
    size_t begin=0;
    while(begin<=text.size())
    {
        size_t end=text.find(',',begin);
        string predictor=text.substr(begin,end==string::npos?string::npos:end-begin);
        bool valid=false;
        for(int direction=0;direction<3;direction++)
            for(const char *order:{"120","021","012"})
                if(predictor=="cubic"+to_string(direction)+"_"+order)
                    valid=true;
        if(!valid)
            throw invalid_argument("invalid predictor in plan: "+predictor);
        predictors.push_back(predictor);
        if(end==string::npos)
            break;
        begin=end+1;
    }
    if(predictors.empty())
        throw invalid_argument("predictor plan cannot be empty");
    return predictors;
}

long double entropy(const vector<qb_t> &qbs,uint64_t &zero_count)
{
    if(qbs.empty())
        return 0;
    unordered_map<qb_t,uint64_t> frequencies;
    for(qb_t qb:qbs)
        frequencies[qb]++;
    long double h1=0;
    zero_count=0;
    for(const auto &[qb,count]:frequencies)
    {
        long double probability=(long double)count/qbs.size();
        h1-=probability*log2(probability);
        if(qb==0)
            zero_count=count;
    }
    return h1;
}

uint64_t append_encoded_layer(const vector<qb_t> &qbs,vector<unsigned char> &stream)
{
    size_t offset=stream.size();
    stream.resize(offset+8);
    uint64_t count=qbs.size();
    for(int byte=0;byte<8;byte++)
        stream[offset+byte]=(count>>(8*byte))&0xff;
    if(qbs.empty())
        return 0;
    huffman_encoder_class<qb_t> encoder;
    encoder.preprocess_encode(qbs.data(),qbs.size());
    uint64_t encoded_size=encoder.save_size()+encoder.encode_size();
    offset=stream.size();
    stream.resize(offset+encoded_size);
    unsigned char *cursor=stream.data()+offset;
    encoder.save(cursor);
    encoder.encode(qbs.data(),qbs.size(),cursor);
    if(cursor!=stream.data()+stream.size())
        throw runtime_error("Huffman encoded size mismatch");
    return encoded_size;
}

template<typename T>
void compress_block(asz::param_c<T> &param,const string &predictor,vector<qb_t> &qbs,vector<vector<uint64_t>> &block_loc,vector<uint64_t> &stride,T best_t,T layer_eb)
{
    unsigned char direction=predictor[5]-'0';
    unsigned char order=predictor[9]-'0';
    param.block_compress(qbs,block_loc,stride,best_t,layer_eb,direction,order);
}

template<typename T>
family_result_c evaluate_family(asz::param_c<T> &param,const vector<point_t> &target_blocks,const string &family,const string &seed_mode)
{
    auto total_begin=chrono::steady_clock::now();
    uint64_t layer_num=param.predictor_vec.size();
    if(target_blocks.empty())
        throw invalid_argument("at least one target block is required");
    T seed_eb;
    if(seed_mode=="pivot")
        seed_eb=param.abs_eb*param.pivot_eb_ratio;
    else if(seed_mode=="first-layer")
        seed_eb=param.abs_eb*pow(param.eb_ratio,(int64_t)layer_num-1);
    else
        throw invalid_argument("seed mode must be pivot or first-layer");
    if(!(seed_eb>0))
        throw runtime_error("seed error bound must be positive");
    param.force_quintic=family=="quintic";
    if(family!="cubic"&&family!="quintic")
        throw invalid_argument("family must be cubic or quintic");
    param.layer_diagnostics.enabled=true;
    param.layer_diagnostics.reset(layer_num);
    family_result_c result;
    result.family=family;
    result.seed_mode=seed_mode;
    result.seed_eb=seed_eb;
    vector<vector<qb_t>> layer_qbs(layer_num);
    vector<qb_t> context_qbs;
    auto initialization_begin=chrono::steady_clock::now();
    if(param.compressed_data.size()!=param.data.size())
        param.compressed_data=param.data;
    result.initialization_seconds=elapsed_seconds(initialization_begin);
    auto simulation_begin=chrono::steady_clock::now();
    for(const point_t &target_block:target_blocks)
    {
        point_t context_block_begin,target_block_end,context_begin,context_end;
        for(int axis=0;axis<3;axis++)
        {
            if(target_block[axis]>=param.block_num[axis])
                throw invalid_argument("target block is outside local block grid");
            context_block_begin[axis]=target_block[axis]?target_block[axis]-1:0;
            target_block_end[axis]=target_block[axis]+1;
            context_begin[axis]=context_block_begin[axis]*param.block_shape[axis];
            context_end[axis]=min(target_block_end[axis]*param.block_shape[axis]+1,param.data_shape[axis]);
        }
        for(uint64_t i0=context_begin[0];i0<context_end[0];i0+=param.pivot_stride[0])
        for(uint64_t i1=context_begin[1];i1<context_end[1];i1+=param.pivot_stride[1])
        for(uint64_t i2=context_begin[2];i2<context_end[2];i2+=param.pivot_stride[2])
        {
            uint64_t pos=(i0*param.data_shape[1]+i1)*param.data_shape[2]+i2;
            qb_t qb=(qb_t)llround((double)param.data[pos]/(2*(double)seed_eb));
            param.compressed_data[pos]=(T)((double)qb*2*(double)seed_eb);
            result.pivot_count++;
        }
        for(uint64_t block_i0=context_block_begin[0];block_i0<target_block_end[0];block_i0++)
        for(uint64_t block_i1=context_block_begin[1];block_i1<target_block_end[1];block_i1++)
        for(uint64_t block_i2=context_block_begin[2];block_i2<target_block_end[2];block_i2++)
        {
            bool target=block_i0==target_block[0]&&block_i1==target_block[1]&&block_i2==target_block[2];
            vector<vector<uint64_t>> block_loc(3);
            block_loc[0]={block_i0*param.block_shape[0],min((block_i0+1)*param.block_shape[0]+1,param.data_shape[0])};
            block_loc[1]={block_i1*param.block_shape[1],min((block_i1+1)*param.block_shape[1]+1,param.data_shape[1])};
            block_loc[2]={block_i2*param.block_shape[2],min((block_i2+1)*param.block_shape[2]+1,param.data_shape[2])};
            auto stride=param.pivot_stride;
            for(uint64_t layer_id=0;layer_id<layer_num;layer_id++)
            {
                const string &predictor=param.predictor_vec[layer_id];
                T layer_eb=param.abs_eb*pow(param.eb_ratio,(int64_t)layer_num-(int64_t)layer_id-1);
                T layer_default_slope=param.default_slope*pow(param.slope_ratio,(int64_t)layer_num-(int64_t)layer_id-1);
                bool used_fallback=false;
                T best_t=param.select_block_coefficient(predictor,block_loc,stride,layer_eb,layer_default_slope,used_fallback);
                vector<qb_t> &qbs=target?layer_qbs[layer_id]:context_qbs;
                if(!target)
                    context_qbs.clear();
                param.layer_diagnostics.enabled=target;
                param.layer_diagnostics.current_layer=layer_id;
                compress_block(param,predictor,qbs,block_loc,stride,best_t,layer_eb);
                unsigned char direction=predictor[5]-'0';
                stride[direction]/=2;
            }
        }
        for(uint64_t i0=context_begin[0];i0<context_end[0];i0++)
        for(uint64_t i1=context_begin[1];i1<context_end[1];i1++)
        {
            uint64_t pos=(i0*param.data_shape[1]+i1)*param.data_shape[2]+context_begin[2];
            copy(param.data.begin()+pos,param.data.begin()+pos+context_end[2]-context_begin[2],param.compressed_data.begin()+pos);
        }
    }
    result.simulation_seconds=elapsed_seconds(simulation_begin);
    param.layer_diagnostics.enabled=false;
    result.layer_counts.resize(layer_num);
    result.layer_huffman_bytes.resize(layer_num);
    result.layer_prediction_mse.resize(layer_num);
    result.layer_prediction_mae.resize(layer_num);
    result.layer_reconstruction_mse.resize(layer_num);
    result.layer_reconstruction_mae.resize(layer_num);
    result.layer_reconstruction_psnr.resize(layer_num);
    result.layer_h1.resize(layer_num);
    result.layer_zero_fraction.resize(layer_num);
    result.layer_huffman_bps.resize(layer_num);
    auto statistics_begin=chrono::steady_clock::now();
    long double prediction_sse=0,prediction_sae=0,reconstruction_sse=0,reconstruction_sae=0,weighted_entropy=0;
    uint64_t total_zero=0;
    long double value_range=(long double)param.max_val-param.min_val;
    for(uint64_t layer_id=0;layer_id<layer_num;layer_id++)
    {
        uint64_t count=param.layer_diagnostics.count[layer_id];
        if(count!=layer_qbs[layer_id].size())
            throw runtime_error("target layer diagnostic count mismatch");
        if(count==0)
            continue;
        uint64_t zero_count=0;
        long double h1=entropy(layer_qbs[layer_id],zero_count);
        result.layer_counts[layer_id]=count;
        result.layer_prediction_mse[layer_id]=param.layer_diagnostics.prediction_squared_error[layer_id]/count;
        result.layer_prediction_mae[layer_id]=param.layer_diagnostics.prediction_absolute_error[layer_id]/count;
        result.layer_reconstruction_mse[layer_id]=param.layer_diagnostics.reconstruction_squared_error[layer_id]/count;
        result.layer_reconstruction_mae[layer_id]=param.layer_diagnostics.reconstruction_absolute_error[layer_id]/count;
        result.layer_reconstruction_psnr[layer_id]=result.layer_reconstruction_mse[layer_id]==0?INFINITY:10*log10(value_range*value_range/result.layer_reconstruction_mse[layer_id]);
        result.layer_h1[layer_id]=h1;
        result.layer_zero_fraction[layer_id]=(long double)zero_count/count;
        result.target_count+=count;
        total_zero+=zero_count;
        prediction_sse+=param.layer_diagnostics.prediction_squared_error[layer_id];
        prediction_sae+=param.layer_diagnostics.prediction_absolute_error[layer_id];
        reconstruction_sse+=param.layer_diagnostics.reconstruction_squared_error[layer_id];
        reconstruction_sae+=param.layer_diagnostics.reconstruction_absolute_error[layer_id];
        weighted_entropy+=h1*count;
    }
    if(result.target_count==0)
        throw runtime_error("sample contains no target points");
    result.prediction_mse=prediction_sse/result.target_count;
    result.prediction_mae=prediction_sae/result.target_count;
    result.reconstruction_mse=reconstruction_sse/result.target_count;
    result.reconstruction_mae=reconstruction_sae/result.target_count;
    result.reconstruction_psnr=result.reconstruction_mse==0?INFINITY:10*log10(value_range*value_range/result.reconstruction_mse);
    result.weighted_h1=weighted_entropy/result.target_count;
    result.zero_fraction=(long double)total_zero/result.target_count;
    result.statistics_seconds=elapsed_seconds(statistics_begin);
    auto lossless_begin=chrono::steady_clock::now();
    vector<unsigned char> huffman_stream;
    for(uint64_t layer_id=0;layer_id<layer_num;layer_id++)
    {
        uint64_t huffman_bytes=append_encoded_layer(layer_qbs[layer_id],huffman_stream);
        result.layer_huffman_bytes[layer_id]=huffman_bytes;
        result.layer_huffman_bps[layer_id]=result.layer_counts[layer_id]?(long double)8*huffman_bytes/result.layer_counts[layer_id]:0;
        result.huffman_bytes+=huffman_bytes;
    }
    vector<unsigned char> zstd_stream(ZSTD_compressBound(huffman_stream.size()));
    result.zstd_bytes=ZSTD_compress(zstd_stream.data(),zstd_stream.size(),huffman_stream.data(),huffman_stream.size(),3);
    if(ZSTD_isError(result.zstd_bytes))
        throw runtime_error(ZSTD_getErrorName(result.zstd_bytes));
    result.huffman_bps=(long double)8*result.huffman_bytes/result.target_count;
    result.zstd_bps=(long double)8*result.zstd_bytes/result.target_count;
    result.lossless_seconds=elapsed_seconds(lossless_begin);
    result.total_seconds=elapsed_seconds(total_begin);
    return result;
}

void print_result(const family_result_c &result,const vector<string> &plan)
{
    cout<<setprecision(12)<<scientific;
    cout<<"Family sample: family="<<result.family<<", seed_mode="<<result.seed_mode<<", seed_eb="<<result.seed_eb<<", pivots="<<result.pivot_count<<", points="<<result.target_count<<", prediction_mse="<<result.prediction_mse<<", prediction_mae="<<result.prediction_mae<<", reconstruction_mse="<<result.reconstruction_mse<<", reconstruction_mae="<<result.reconstruction_mae<<", reconstruction_psnr="<<result.reconstruction_psnr<<", h1="<<result.weighted_h1<<", zero_fraction="<<result.zero_fraction<<", huffman_bytes="<<result.huffman_bytes<<", huffman_bps="<<result.huffman_bps<<", zstd_bytes="<<result.zstd_bytes<<", zstd_bps="<<result.zstd_bps<<", initialization_seconds="<<result.initialization_seconds<<", simulation_seconds="<<result.simulation_seconds<<", statistics_seconds="<<result.statistics_seconds<<", h1_psnr_seconds="<<result.initialization_seconds+result.simulation_seconds+result.statistics_seconds<<", lossless_seconds="<<result.lossless_seconds<<", total_seconds="<<result.total_seconds<<'\n';
    for(uint64_t layer=0;layer<plan.size();layer++)
        cout<<"Sample layer: family="<<result.family<<", seed_mode="<<result.seed_mode<<", layer="<<layer<<", predictor="<<plan[layer]<<", points="<<result.layer_counts[layer]<<", prediction_mse="<<result.layer_prediction_mse[layer]<<", prediction_mae="<<result.layer_prediction_mae[layer]<<", reconstruction_mse="<<result.layer_reconstruction_mse[layer]<<", reconstruction_mae="<<result.layer_reconstruction_mae[layer]<<", reconstruction_psnr="<<result.layer_reconstruction_psnr[layer]<<", h1="<<result.layer_h1[layer]<<", zero_fraction="<<result.layer_zero_fraction[layer]<<", huffman_bytes="<<result.layer_huffman_bytes[layer]<<", huffman_bps="<<result.layer_huffman_bps[layer]<<'\n';
}

template<typename T>
void prepare_param(asz::param_c<T> &param,const vector<string> &full_plan,uint64_t suffix_layers)
{
    if(suffix_layers==0||suffix_layers>full_plan.size())
        throw invalid_argument("suffix layer count is outside predictor plan");
    param.get_default_slope();
    param.predictor_vec.assign(full_plan.end()-suffix_layers,full_plan.end());
    param.generate_pivot_stride_and_block_shape_and_block_num();
}

vector<point_t> make_stratified_targets(const vector<uint64_t> &block_num,uint64_t sample_count)
{
    uint64_t total=block_num[0]*block_num[1]*block_num[2];
    if(sample_count==0)
        throw invalid_argument("sample block count must be positive");
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

void self_test()
{
    asz::param_c<float> param;
    param.data_shape={33,33,33};
    param.data.resize(33*33*33);
    for(uint64_t i=0;i<33;i++)
        for(uint64_t j=0;j<33;j++)
            for(uint64_t k=0;k<33;k++)
                param.data[(i*33+j)*33+k]=sin((double)i/7)+cos((double)j/9)+(double)k*k/2048;
    auto [minimum_it,maximum_it]=minmax_element(param.data.begin(),param.data.end());
    param.min_val=*minimum_it;
    param.max_val=*maximum_it;
    param.rel_eb=1e-3;
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);
    vector<string> plan={"cubic0_012","cubic1_012","cubic2_012","cubic0_012","cubic1_012","cubic2_012"};
    prepare_param(param,plan,6);
    vector<point_t> targets={{0,0,0},{1,1,1}};
    auto cubic=evaluate_family(param,targets,"cubic","first-layer");
    auto quintic=evaluate_family(param,targets,"quintic","first-layer");
    if(cubic.target_count==0||cubic.target_count!=quintic.target_count||!isfinite((double)cubic.reconstruction_mse)||!isfinite((double)quintic.reconstruction_mse))
        throw runtime_error("self-test produced invalid metrics");
    cout<<"PASS: range sampling and family evaluation\n";
}

int main(int argc,char **argv)
{
    try
    {
        if(argc==2&&string(argv[1])=="--self-test")
        {
            self_test();
            return 0;
        }
        if(argc!=11&&argc!=12)
            throw invalid_argument("usage: s10_predictor_family_block_sample input dim0 dim1 dim2 rel_eb predictor_plan suffix_layers block0 block1 block2 pivot|first-layer OR ... suffix_layers sample sample_count pivot|first-layer");
        asz::param_c<float> param;
        string input_path=argv[1];
        param.data_shape={stoull(argv[2]),stoull(argv[3]),stoull(argv[4])};
        param.rel_eb=stof(argv[5]);
        vector<string> full_plan=parse_predictor_plan(argv[6]);
        uint64_t suffix_layers=stoull(argv[7]);
        bool stratified=string(argv[8])=="sample";
        if((stratified&&argc!=11)||(!stratified&&argc!=12))
            throw invalid_argument("invalid target block arguments");
        string seed_mode=stratified?argv[10]:argv[11];
        uint64_t count=param.data_shape[0]*param.data_shape[1]*param.data_shape[2];
        param.data.resize(count);
        ifstream input(input_path,ios::binary);
        input.read(reinterpret_cast<char *>(param.data.data()),count*sizeof(float));
        if(!input)
            throw runtime_error("input size does not match tensor shape");
        auto [minimum_it,maximum_it]=minmax_element(param.data.begin(),param.data.end());
        param.min_val=*minimum_it;
        param.max_val=*maximum_it;
        if(param.min_val==param.max_val)
            throw runtime_error("constant input");
        param.abs_eb=param.rel_eb*(param.max_val-param.min_val);
        prepare_param(param,full_plan,suffix_layers);
        vector<point_t> target_blocks;
        if(stratified)
            target_blocks=make_stratified_targets(param.block_num,stoull(argv[9]));
        else
            target_blocks.push_back({stoull(argv[8]),stoull(argv[9]),stoull(argv[10])});
        cout<<"Sample config: suffix_layers="<<suffix_layers<<", targets="<<target_blocks.size()<<", pivot_stride={"<<param.pivot_stride[0]<<','<<param.pivot_stride[1]<<','<<param.pivot_stride[2]<<"}, block_shape={"<<param.block_shape[0]<<','<<param.block_shape[1]<<','<<param.block_shape[2]<<"}, block_num={"<<param.block_num[0]<<','<<param.block_num[1]<<','<<param.block_num[2]<<"}, global_range="<<param.max_val-param.min_val<<'\n';
        auto cubic=evaluate_family(param,target_blocks,"cubic",seed_mode);
        print_result(cubic,param.predictor_vec);
        auto quintic=evaluate_family(param,target_blocks,"quintic",seed_mode);
        print_result(quintic,param.predictor_vec);
        cout<<setprecision(12)<<scientific;
        cout<<"Family comparison: seed_mode="<<seed_mode<<", reconstruction_mse_ratio_1d6r_to_1d4r="<<quintic.reconstruction_mse/cubic.reconstruction_mse<<", prediction_mse_ratio_1d6r_to_1d4r="<<quintic.prediction_mse/cubic.prediction_mse<<", h1_delta_1d6r_minus_1d4r="<<quintic.weighted_h1-cubic.weighted_h1<<", huffman_bps_delta_1d6r_minus_1d4r="<<quintic.huffman_bps-cubic.huffman_bps<<", zstd_bps_delta_1d6r_minus_1d4r="<<quintic.zstd_bps-cubic.zstd_bps<<", h1_psnr_selector_seconds="<<cubic.initialization_seconds+cubic.simulation_seconds+cubic.statistics_seconds+quintic.initialization_seconds+quintic.simulation_seconds+quintic.statistics_seconds<<", lossless_seconds="<<cubic.lossless_seconds+quintic.lossless_seconds<<", measured_total_seconds="<<cubic.total_seconds+quintic.total_seconds<<'\n';
    }
    catch(const exception &error)
    {
        cerr<<error.what()<<'\n';
        return 1;
    }
    return 0;
}
