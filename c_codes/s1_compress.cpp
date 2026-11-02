#include "asz_core/asz_param.hpp"

using namespace std;

vector<string> parse_predictor_plan(const string &text)
{
    vector<string> predictors;
    size_t begin=0;
    while (begin<=text.size())
    {
        size_t end=text.find(',',begin);
        string predictor=text.substr(begin,end==string::npos?string::npos:end-begin);
        bool valid=false;
        for (int direction=0;direction<3;direction++)
            for (const char *traversal_order:{"120","021","012"})
                if (predictor=="cubic"+to_string(direction)+"_"+traversal_order)
                    valid=true;
        if (!valid)
            throw invalid_argument("invalid predictor in plan: "+predictor);
        predictors.push_back(predictor);
        if (end==string::npos)
            break;
        begin=end+1;
    }
    if (predictors.empty())
        throw invalid_argument("predictor plan cannot be empty");
    return predictors;
}

template<typename T>
void prepare_compression_plan(asz::param_c<T> &param,const vector<string> &predictor_plan)
{
    param.get_default_slope();
    printf("default_slope=%f\n",param.default_slope);
    if (predictor_plan.empty())
        param.generate_config("compress");
    else
    {
        param.predictor_vec=predictor_plan;
        param.generate_pivot_stride_and_block_shape_and_block_num();
    }
    if (param.predictor_vec.size()>63)
        throw invalid_argument("predictor plan cannot contain more than 63 layers");
    if (param.auto_select_predictor_family)
        param.select_predictor_family();
    param.print_config();
}

template<typename T>
void validate_parameters(asz::param_c<T> &param,bool t_min_set,bool t_max_set)
{
    if(!(param.pivot_eb_ratio>0&&param.pivot_eb_ratio<=1))
        throw invalid_argument("pivot_eb_ratio must be in (0,1]");
    if(!(param.eb_ratio>0&&param.eb_ratio<=1))
        throw invalid_argument("eb_ratio must be in (0,1]");
    if(!(param.slope_ratio>0&&param.slope_ratio<=1))
        throw invalid_argument("slope_ratio must be in (0,1]");
    if(param.block_pivot_ratio==0)
        throw invalid_argument("block_pivot_ratio must be positive");
    if(param.max_layer_num==0||param.max_layer_num>63)
        throw invalid_argument("max_layer_num must be in [1,63]");
    if(param.full_predictor_search_layer_num==0||param.full_predictor_search_layer_num>63)
        throw invalid_argument("full_predictor_search_layer_num must be in [1,63]");
    if(param.generate_config_sample_stride==0)
        throw invalid_argument("generate_config_sample_stride must be positive");
    if(param.h1_block_sampling_num==0)
        throw invalid_argument("h1_block_sampling_num must be positive");
    if(!(param.stat_eb_ratio>0&&param.stat_eb_ratio<=1))
        throw invalid_argument("stat_eb_ratio must be in (0,1]");
    if(param.predictor_family_suffix_layers==0)
        throw invalid_argument("predictor_family_suffix_layers must be positive");
    if(param.predictor_family_sample_blocks==0)
        throw invalid_argument("predictor_family_sample_blocks must be positive");
    if(param.predictor_family_sample_point_limit==0)
        throw invalid_argument("predictor_family_sample_point_limit must be positive");
    if(!(param.predictor_family_sample_fraction_limit>0&&param.predictor_family_sample_fraction_limit<=1))
        throw invalid_argument("predictor_family_sample_fraction_limit must be in (0,1]");
    if(param.predictor_family_coarse_probe_block_pivot_ratio==0||param.predictor_family_fine_probe_block_pivot_ratio==0)
        throw invalid_argument("predictor family probe block pivot ratios must be positive");
    if(!(param.predictor_family_fine_eb_threshold>0&&isfinite(param.predictor_family_fine_eb_threshold)))
        throw invalid_argument("predictor_family_fine_eb_threshold must be positive and finite");
    if(!(param.default_slope_invalid_ratio_threshold>0&&param.default_slope_invalid_ratio_threshold<=1))
        throw invalid_argument("default_slope_invalid_ratio_threshold must be in (0,1]");
    if(!(param.default_slope_fallback>0&&isfinite(param.default_slope_fallback)))
        throw invalid_argument("default_slope_fallback must be positive and finite");
    if(!(param.default_slope_eb_span>1&&isfinite(param.default_slope_eb_span)))
        throw invalid_argument("default_slope_eb_span must be greater than 1 and finite");
    if(param.t_precision<16||param.t_precision%16!=0)
        throw invalid_argument("t_precision must be a positive multiple of 16");
    if(t_min_set!=t_max_set)
        throw invalid_argument("t_min and t_max must be supplied together");
    if(!(param.t_min>=0&&param.t_min<=param.t_max&&param.t_max<=0.5))
        throw invalid_argument("t range must satisfy 0 <= t_min <= t_max <= 0.5");
    if(abs(param.t_min*param.t_precision-round(param.t_min*param.t_precision))>1e-6||abs(param.t_max*param.t_precision-round(param.t_max*param.t_precision))>1e-6)
        throw invalid_argument("t_min and t_max must be representable at t_precision");
    if(param.t_min>(T)4/16||param.t_max<(T)5/16)
        throw invalid_argument("t range must include 4/16 and 5/16");
    param.set_t_candidates();
}

template<typename T>
void load_input(asz::param_c<T> &param)
{
    if(param.original_data_path.empty()||param.compressed_data_path.empty())
        throw invalid_argument("input and compressed-output paths are required");
    if(param.data_shape.size()!=3||any_of(param.data_shape.begin(),param.data_shape.end(),[](uint64_t size){return size<7;}))
        throw invalid_argument("all three dimensions must be at least 7");
    if(!(param.rel_eb>0&&isfinite(param.rel_eb)))
        throw invalid_argument("relative error bound must be positive and finite");
    uint64_t data_size=1;
    for(uint64_t size:param.data_shape)
    {
        if(data_size>numeric_limits<uint64_t>::max()/size)
            throw invalid_argument("data dimensions overflow the element count");
        data_size*=size;
    }
    if(data_size>numeric_limits<size_t>::max()/sizeof(T))
        throw invalid_argument("data dimensions exceed the addressable input size");
    param.data.resize(data_size);
    ifstream input(param.original_data_path,ios::binary);
    if(!input)
        throw runtime_error("cannot open input: "+param.original_data_path);
    input.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(T));
    if(!input)
        throw runtime_error("cannot read complete input: "+param.original_data_path);
    if(input.peek()!=char_traits<char>::eof())
        throw runtime_error("input size does not match the dimensions: "+param.original_data_path);
    for(T value:param.data)
        if(!isfinite(value))
            throw runtime_error("input contains a nonfinite value: "+param.original_data_path);
    auto range_start_time=chrono::high_resolution_clock::now();
    auto [minimum,maximum]=minmax_element(param.data.begin(),param.data.end());
    param.min_val=*minimum;
    param.max_val=*maximum;
    param.data_range_time=chrono::duration<double>(chrono::high_resolution_clock::now()-range_start_time).count();
    if(param.min_val==param.max_val)
        throw runtime_error("max_val==min_val");
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);
    printf("Data range time: %f s\n",param.data_range_time);
}

template<typename T>
void write_compressed_stream(const asz::param_c<T> &param)
{
    ofstream output(param.compressed_data_path,ios::binary);
    if(!output)
        throw runtime_error("cannot open compressed output: "+param.compressed_data_path);
    output.write(reinterpret_cast<const char*>(param.zstd_bs_vec.data()),param.zstd_bs_vec.size());
    if(!output)
        throw runtime_error("cannot write compressed output: "+param.compressed_data_path);
}

int main(int argc,char* argv[]) try
{
    if(argc==2&&string(argv[1])=="--help")
    {
        printf("usage: s1_compress -i INPUT -z COMPRESSED -o RECONSTRUCTED -3 DIM0 DIM1 DIM2 -M REL REL_EB [options]\n");
        return 0;
    }
    auto param=asz::param_c<float>();
    vector<string> predictor_plan;
    bool t_min_set=false,t_max_set=false;
    for (int i=1;i<argc;i++)
    {
        string arg=argv[i];
        if (arg=="-f")
            continue;
        else if (arg=="-i")
        {
            param.original_data_path=argv[++i];
            param.compressed_data_path=param.original_data_path+".asz";
            param.decompressed_data_path=param.compressed_data_path+".bin";
            continue;
        }
        else if (arg=="-z")
        {
            param.compressed_data_path=argv[++i];
            param.decompressed_data_path=param.compressed_data_path+".bin";
            continue;
        }
        else if (arg=="-o")
        {
            param.decompressed_data_path=argv[++i];
            continue;
        }
        else if (arg=="-3")
        {
            param.data_shape={stoul(argv[++i]),stoul(argv[++i]),stoul(argv[++i])};
            continue;
        }
        else if (arg=="-M")
        {
            i++;
            param.rel_eb=stof(argv[++i]);
            continue;
        }
        else if (arg=="--predictor-plan")
        {
            predictor_plan=parse_predictor_plan(argv[++i]);
            continue;
        }
        else if (arg=="--predictor-family")
        {
            string family=argv[++i];
            param.auto_select_predictor_family=false;
            if (family=="cubic")
                param.force_quintic=false;
            else if (family=="quintic")
                param.force_quintic=true;
            else
                throw invalid_argument("predictor_family must be cubic or quintic");
            continue;
        }
        else if (arg=="--pivot-eb-ratio")
        {
            param.pivot_eb_ratio=stof(argv[++i]);
            continue;
        }
        else if (arg=="--eb-ratio")
        {
            param.eb_ratio=stof(argv[++i]);
            continue;
        }
        else if (arg=="--slope-ratio")
        {
            param.slope_ratio=stof(argv[++i]);
            continue;
        }
        else if (arg=="--block-pivot-ratio")
        {
            param.block_pivot_ratio=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--max-layer-num")
        {
            param.max_layer_num=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--full-predictor-search-layer-num")
        {
            param.full_predictor_search_layer_num=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--generate-config-sample-stride")
        {
            param.generate_config_sample_stride=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--h1-block-sampling-num")
        {
            param.h1_block_sampling_num=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--stat-eb-ratio")
        {
            param.stat_eb_ratio=stof(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-suffix-layers")
        {
            param.predictor_family_suffix_layers=stoull(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-sample-blocks")
        {
            param.predictor_family_sample_blocks=stoull(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-sample-point-limit")
        {
            param.predictor_family_sample_point_limit=stoull(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-sample-fraction-limit")
        {
            param.predictor_family_sample_fraction_limit=stof(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-coarse-probe-block-pivot-ratio")
        {
            param.predictor_family_coarse_probe_block_pivot_ratio=stoull(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-fine-probe-block-pivot-ratio")
        {
            param.predictor_family_fine_probe_block_pivot_ratio=stoull(argv[++i]);
            continue;
        }
        else if(arg=="--predictor-family-fine-eb-threshold")
        {
            param.predictor_family_fine_eb_threshold=stof(argv[++i]);
            continue;
        }
        else if (arg=="--default-slope-invalid-ratio-threshold")
        {
            param.default_slope_invalid_ratio_threshold=stof(argv[++i]);
            continue;
        }
        else if (arg=="--default-slope-fallback")
        {
            param.default_slope_fallback=stof(argv[++i]);
            continue;
        }
        else if (arg=="--default-slope-eb-span")
        {
            param.default_slope_eb_span=stof(argv[++i]);
            continue;
        }
        else if (arg=="--t-precision")
        {
            param.t_precision=stoi(argv[++i]);
            continue;
        }
        else if (arg=="--t-min")
        {
            param.t_min=stof(argv[++i]);
            t_min_set=true;
            continue;
        }
        else if (arg=="--t-max")
        {
            param.t_max=stof(argv[++i]);
            t_max_set=true;
            continue;
        }
        else if (arg=="--report-t-histogram")
        {
            param.report_t_histogram=true;
            continue;
        }
        else
            throw invalid_argument("unknown argument: "+arg);
    }

    validate_parameters(param,t_min_set,t_max_set);
    load_input(param);
    prepare_compression_plan(param,predictor_plan);
    param.compress();
    write_compressed_stream(param);
    return 0;
}
catch(const exception &error)
{
    fprintf(stderr,"error: %s\n",error.what());
    return 1;
}
