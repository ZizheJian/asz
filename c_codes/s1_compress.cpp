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
void prepare_config(asz::param_c<T> &param,const vector<string> &predictor_plan)
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

int main(int argc,char* argv[])
{
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
        else if (arg=="--predictor-family-sample-limit")
        {
            param.predictor_family_sample_limit=stoull(argv[++i]);
            continue;
        }
        else if (arg=="--predictor-family-mse-ratio-threshold")
        {
            param.predictor_family_mse_ratio_threshold=stof(argv[++i]);
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
        else if (arg=="--t-policy")
        {
            param.t_policy=argv[++i];
            continue;
        }
        else if (arg=="--block-t-policy")
        {
            param.block_t_policy=argv[++i];
            continue;
        }
        else if (arg=="--report-t-histogram")
        {
            param.report_t_histogram=true;
            continue;
        }
    }

    if (!(param.pivot_eb_ratio>0&&param.pivot_eb_ratio<=1))
        throw invalid_argument("pivot_eb_ratio must be in (0,1]");
    if (!(param.eb_ratio>0&&param.eb_ratio<=1))
        throw invalid_argument("eb_ratio must be in (0,1]");
    if (!(param.slope_ratio>0&&param.slope_ratio<=1))
        throw invalid_argument("slope_ratio must be in (0,1]");
    if (param.block_pivot_ratio==0)
        throw invalid_argument("block_pivot_ratio must be positive");
    if (param.max_layer_num==0||param.max_layer_num>63)
        throw invalid_argument("max_layer_num must be in [1,63]");
    if (param.full_predictor_search_layer_num==0||param.full_predictor_search_layer_num>63)
        throw invalid_argument("full_predictor_search_layer_num must be in [1,63]");
    if (param.generate_config_sample_stride==0)
        throw invalid_argument("generate_config_sample_stride must be positive");
    if (param.h1_block_sampling_num==0)
        throw invalid_argument("h1_block_sampling_num must be positive");
    if (!(param.stat_eb_ratio>0&&param.stat_eb_ratio<=1))
        throw invalid_argument("stat_eb_ratio must be in (0,1]");
    if (param.predictor_family_sample_limit==0)
        throw invalid_argument("predictor_family_sample_limit must be positive");
    if (!(param.predictor_family_mse_ratio_threshold>=0&&isfinite(param.predictor_family_mse_ratio_threshold)))
        throw invalid_argument("predictor_family_mse_ratio_threshold must be nonnegative and finite");
    if (!(param.default_slope_invalid_ratio_threshold>0&&param.default_slope_invalid_ratio_threshold<=1))
        throw invalid_argument("default_slope_invalid_ratio_threshold must be in (0,1]");
    if (!(param.default_slope_fallback>0&&isfinite(param.default_slope_fallback)))
        throw invalid_argument("default_slope_fallback must be positive and finite");
    if (!(param.default_slope_eb_span>1&&isfinite(param.default_slope_eb_span)))
        throw invalid_argument("default_slope_eb_span must be greater than 1 and finite");
    if (param.t_precision<16||param.t_precision%16!=0)
        throw invalid_argument("t_precision must be a positive multiple of 16");
    if (t_min_set!=t_max_set)
        throw invalid_argument("t_min and t_max must be supplied together");
    if (!(param.t_min>=0&&param.t_min<=param.t_max&&param.t_max<=0.5))
        throw invalid_argument("t range must satisfy 0 <= t_min <= t_max <= 0.5");
    if (abs(param.t_min*param.t_precision-round(param.t_min*param.t_precision))>1e-6||abs(param.t_max*param.t_precision-round(param.t_max*param.t_precision))>1e-6)
        throw invalid_argument("t_min and t_max must be representable at t_precision");
    if (param.t_min>(float)4/16||param.t_max<(float)5/16)
        throw invalid_argument("t range must include 4/16 and 5/16");
    param.set_t_policy(param.t_policy);

    param.data.resize(param.data_shape[0]*param.data_shape[1]*param.data_shape[2]);
    ifstream data_file(param.original_data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    if (param.min_val==param.max_val)
        throw runtime_error("max_val==min_val");
    
    auto param_double=asz::param_c<double>();
    if (param.rel_eb<1e-5)
    {
        param_double.copy_from(param);
        param_double.abs_eb=param_double.rel_eb*(param_double.max_val-param_double.min_val);
        prepare_config(param_double,predictor_plan);
        param_double.compress();
        param.copy_from(param_double);
    }
    else
    {
        param.abs_eb=param.rel_eb*(param.max_val-param.min_val);
        prepare_config(param,predictor_plan);
        param.compress();
    }
    ofstream compressed_data_file(param.compressed_data_path,ios::binary);
    if (!compressed_data_file)
        throw runtime_error("cannot open compressed output: "+param.compressed_data_path);
    compressed_data_file.write(reinterpret_cast<const char*>(param.zstd_bs_vec.data()),param.zstd_bs_vec.size());
    if (!compressed_data_file)
        throw runtime_error("cannot write compressed output: "+param.compressed_data_path);
    compressed_data_file.close();
    return 0;
}
