#include "asz_core/asz_param.hpp"

using namespace std;

// 估计斜率的时候要鲁邦一些，包括另外两个eb要更远、对nan的处理
// 可能有些情况下需要用H1来选择predictor

int main()
{
    srand(time(NULL));
    auto param=asz::param_c();
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    // param.data_shape={100,500,500};
    param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Miranda/density.f32.dat";
    param.data_shape={256,384,384};
    // param.original_data_path="/lcrc/project/SDR/zjian-in-SDR/APSU_TestData_004.h5.f32_center.bin";
    // param.data_shape={205,312,363};
    // param.original_data_path="/lcrc/project/SDR/zjian-in-SDR/Avg_L0470_Double_exp_elong_siemens_1p00sampit_0p05inplane_patch1_of1_part0_001.h5.f32_center.bin";
    // param.data_shape={150,454,390};
    // param.original_data_path="/lcrc/project/SDR/zjian-in-SDR/baryon_density.f32_center.bin";
    // param.data_shape={256,256,256};
    // param.original_data_path="/lcrc/project/SDR/zjian-in-SDR/CLDICE_26x1800x3600.dat_center.bin";
    // param.data_shape={13,900,1800};
    // param.original_data_path="/lcrc/project/SDR/zjian-in-SDR/PRES-98x1200x1200.dat_center.bin";
    // param.data_shape={49,600,600};
    // param.original_data_path="/lcrc/project/ECP-EZ/aramco/aramco-snapshot-1800.f32";
    // param.data_shape={449,449,235};
    param.rel_eb=1e-6;

    param.data.resize(param.data_shape[0]*param.data_shape[1]*param.data_shape[2]);
    ifstream data_file(param.original_data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);

    //////// 获得基准斜率 ////////
    param.get_default_slope();
    printf("default_slope=%f\n",param.default_slope);
    exit(0);

    //////// 直接生成配置 ////////
    // param.generate_config();
    // printf("pivot_eb_ratio=%f\n",param.pivot_eb_ratio);
    // printf("eb_ratio=%f\n",param.eb_ratio);
    // for (auto predictor:param.predictor_vec)
    //     printf("\"%s\",",predictor.c_str());
    // printf("\n");
    // param.compress();
    // exit(0);

    //////// 搜索配置 ////////
    float best_dist=0;
    for (int attempt=0;attempt<100;attempt++)
    {
        asz::param_c backup_param;
        backup_param.copy_from(param);
        param.generate_config_enumerate();
        float dist=param.compress();
        if (dist<best_dist)
            param.copy_from(backup_param);
        else
        {
            printf("Found better configuration\n");
            best_dist=dist;
        }
        printf("\n");
    }
    param.print_config();
}