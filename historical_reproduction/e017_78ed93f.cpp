#include "asz_core/asz_param.hpp"

using namespace std;

int main(int argc,char **argv)
{
    if(argc!=2)
    {
        cerr<<"usage: e017_78ed93f REL_EB\n";
        return 2;
    }
    auto param=asz::param_c();
    param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32";
    param.data_shape={1024,1813,1558};
    param.rel_eb=stof(argv[1]);
    uint64_t data_num=param.data_shape[0]*param.data_shape[1]*param.data_shape[2];
    param.data.resize(data_num);
    ifstream data_file(param.original_data_path,ios::binary);
    if(!data_file)
        throw runtime_error("cannot open E017 input");
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    if(!data_file)
        throw runtime_error("cannot read complete E017 input");
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    if(param.min_val==param.max_val)
        throw runtime_error("max_val==min_val");
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);
    cout<<"Historical commit: 78ed93f\n";
    cout<<"Data shape: "<<param.data_shape[0]<<"x"<<param.data_shape[1]<<"x"<<param.data_shape[2]<<"\n";
    cout<<"Relative error bound: "<<param.rel_eb<<"\n";
    auto start_time=chrono::high_resolution_clock::now();
    param.get_default_slope();
    auto end_time=chrono::high_resolution_clock::now();
    printf("Get default slope time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    printf("default_slope=%f\n",param.default_slope);
    start_time=chrono::high_resolution_clock::now();
    param.generate_config();
    end_time=chrono::high_resolution_clock::now();
    printf("Generate config time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    param.print_config();
    param.compress();
    long double squared_error_sum=0;
    long double max_error=0;
    for(uint64_t i=0;i<param.data.size();i++)
    {
        long double difference=(long double)param.data[i]-param.compressed_data[i];
        squared_error_sum+=difference*difference;
        max_error=max(max_error,abs(difference));
    }
    long double mse=squared_error_sum/param.data.size();
    long double value_range=(long double)param.max_val-param.min_val;
    long double psnr=10*log10(value_range*value_range/mse);
    printf("AUDIT MSE: %.12Lf\n",mse);
    printf("AUDIT PSNR: %.12Lf\n",psnr);
    printf("AUDIT MAX ERROR: %.12Lf\n",max_error);
    return 0;
}
