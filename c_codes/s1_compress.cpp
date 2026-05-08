#include "asz_core/asz_param.hpp"

using namespace std;

// 估计斜率的时候要鲁邦一些，包括另外两个eb要更远、对nan的处理
// 可能有些情况下需要用H1来选择predictor

int main()
{
    srand(time(NULL));
    auto param=asz::param_c();
    // 好
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/embeddings/videollava/embeds_0[(8, 257, 4096)].bin";
    // param.data_shape={8,257,4096};

    // 好，有很多类似数据
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/ISABEL/P/Pf01.bin";
    // param.data_shape={100,500,500};

    // 好，有很多类似数据
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat_center.bin";
    // param.data_shape={13,900,1800};
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/cesm-atm-1.5TB/00/CLDICE_26x1800x3600.dat";
    // param.data_shape={26,1800,3600};

    // 略好
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32_center.bin";
    // param.data_shape={256,256,256};
    param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Nyx-bigdata/NVB_C009_l20n1024_S12345T632_z42/baryon_density.f32";
    param.data_shape={1024,1024,1024};

    // 坏
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/SCALE_LETKF/PRES-98x1200x1200.dat_center.bin";
    // param.data_shape={49,600,600};

    

    // 好，有4个类似数据
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32_center.bin";
    // param.data_shape={205,312,363};
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/APSU_TestData_004/APSU_TestData_004.h5.f32";
    // param.data_shape={1024,1558,1813};

    // 好，有3个类似数据
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32_center.bin";
    // param.data_shape={205,363,312};
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/xpcs_datasets/E017_CeramicGlass_L2Mq0_060C_att00_001/E017_CeramicGlass_L2Mq0_060C_att00_001_001.h5.f32";
    // param.data_shape={1024,1813,1558};

    

    // 坏
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS/9-ID_CSSI_data/benchmarkdata/Avg_L0470_Double_exp_elong_siemens_1p00sampit_0p05inplane_patch1_of1_part0_001.h5.f32_center.bin";
    // param.data_shape={150,454,390};

    // 坏
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/Miranda/density.f32.dat";
    // param.data_shape={256,384,384};

    // 坏
    // param.original_data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/aramco/aramco-snapshot-1800.f32";
    // param.data_shape={449,449,235};

    param.rel_eb=1e-8;

    param.data.resize(param.data_shape[0]*param.data_shape[1]*param.data_shape[2]);
    ifstream data_file(param.original_data_path,ios::binary);
    data_file.read(reinterpret_cast<char*>(param.data.data()),param.data.size()*sizeof(float));
    data_file.close();
    param.min_val=*min_element(param.data.begin(),param.data.end());
    param.max_val=*max_element(param.data.begin(),param.data.end());
    if (param.min_val==param.max_val)
        throw runtime_error("max_val==min_val");
    param.abs_eb=param.rel_eb*(param.max_val-param.min_val);

    //////// 获得基准斜率 ////////
    auto start_time=chrono::high_resolution_clock::now();
    param.get_default_slope();
    auto end_time=chrono::high_resolution_clock::now();
    printf("Get default slope time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    printf("default_slope=%f\n",param.default_slope);

    //////// 直接生成配置 ////////
    start_time=chrono::high_resolution_clock::now();
    param.generate_config();
    end_time=chrono::high_resolution_clock::now();
    printf("Generate config time: %f s\n",chrono::duration<double>(end_time-start_time).count());
    param.print_config();
    param.compress();
    exit(0);

    //////// 搜索配置 ////////
    float best_dist=-1e8;
    for (int attempt=0;attempt<100;attempt++)
    {
        printf("Attempt %d\n",attempt);
        asz::param_c backup_param;
        backup_param.copy_from(param);
        param.generate_config_enumerate();
        float dist=param.compress();
        if (dist<best_dist)
            param.copy_from(backup_param);
        else
        {
            printf("\033[32mFound better configuration\n\033[0m");
            best_dist=dist;
        }
        printf("\n");
    }
    param.print_config();
}