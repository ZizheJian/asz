// 先固定stencil pattern和traversal order，遍历t，计算BR和PSNR
// 再固定stencil pattern，遍历traversal order，计算BR和PSNR
// 用于比较不同stencil pattern的区别

#include <string>
#include <vector>
#include <functional>
#include <cmath>
#include <algorithm>
#include <filesystem>
#include <limits>
#include <unordered_map>
#include "../third_party/csv_tools/c_codes/csv.hpp"

using namespace std;
using namespace csv_tools;

inline void hash_combine(uint64_t &v1,uint64_t v2) //v2应该是std::hash产生的uint64_t
{
    v1^=v2+0x9e3779b97f4a7c15ULL+(v1<<6)+(v1>>2);
}

namespace std
{
    template<>
    struct hash<vector<double>>
    {
        size_t operator()(const vector<double> &v) const
        {
            uint64_t h=0;
            for (auto &x:v)
                hash_combine(h,hash<double>{}(x));
            return h;
        }
    };
}

int main(int argc,char **argv)
try
{
    if (argc==2&&string(argv[1])=="--help")
    {
        printf("usage: s3_conclude_sp_result csv_prefix 1d4r|2d4r|1d6r [output.csv]\n");
        return 0;
    }
    if (argc!=1&&argc!=3&&argc!=4)
        throw runtime_error("use --help for arguments");
    string csv_prefix=argc>=3?argv[1]:"/home/x-zjian1/asz/csv/Pf01";
    string family=argc>=3?argv[2]:"1d6r";
    vector<string> predictor_name_vec;
    if (family=="1d4r"||family=="1d6r")
        predictor_name_vec={family+"0",family+"1",family+"2"};
    else if (family=="2d4r")
        predictor_name_vec={"2d4r01","2d4r02","2d4r12"};
    else
        throw runtime_error("unknown predictor family");
    string output_csv_path=argc==4?argv[3]:csv_prefix+(argc==1?"_each_sp_best.csv":"_"+family+"_each_sp_best.csv");
    if (filesystem::exists(output_csv_path))
        throw runtime_error("output already exists; use a fresh output path");
    vector<string> traversal_order_vec={"xx0","xx1","xx2"};
    vector<string> csv_path_vec;
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
        csv_path_vec.push_back(csv_prefix+"_"+predictor_name+"_"+traversal_order+".csv");
    vector<double> rel_eb_vec;
    vector<vector<double>> t_vec_vec;
    {
        vector<vector<string>> data=read_csv(csv_path_vec[0]);
        if (data.size()<2)
            throw runtime_error("missing or empty sweep CSV: "+csv_path_vec[0]);
        for (int row_id=1;(uint64_t)row_id<data.size();row_id++)
        {
            rel_eb_vec.push_back(stod(data[row_id][0]));
            if ((predictor_name_vec[0].compare(0,4,"1d4r")==0) || (predictor_name_vec[0].compare(0,4,"2d4r")==0))
                t_vec_vec.push_back({stod(data[row_id][1])});
            else
                t_vec_vec.push_back({stod(data[row_id][1]),stod(data[row_id][2])});
        }
        sort(rel_eb_vec.begin(),rel_eb_vec.end(),greater<double>());
        rel_eb_vec.erase(unique(rel_eb_vec.begin(),rel_eb_vec.end()),rel_eb_vec.end());
        sort(t_vec_vec.begin(),t_vec_vec.end(),greater<vector<double>>());
        t_vec_vec.erase(unique(t_vec_vec.begin(),t_vec_vec.end()),t_vec_vec.end());
        if (rel_eb_vec.size()<2)
            throw runtime_error("at least two error bounds are needed to estimate the slope");
    }

    printf("读取原始数据。。。。。。\n");
    // 访问方式是data[csv_path][rel_eb][t_vec][value_name]
    unordered_map<string,unordered_map<double,unordered_map<vector<double>,unordered_map<string,double>>>> data;
    for (auto &csv_path:csv_path_vec)
    {
        vector<vector<string>> temp_data=read_csv(csv_path);
        if (temp_data.size()!=1+rel_eb_vec.size()*t_vec_vec.size())
            throw runtime_error("incomplete coefficient/error-bound grid: "+csv_path);
        for (string metric:{"BR","PSNR"})
            if (find(temp_data[0].begin(),temp_data[0].end(),metric)==temp_data[0].end())
                throw runtime_error("missing metric "+metric+" in "+csv_path);
        for (int row_id=1;(uint64_t)row_id<temp_data.size();row_id++)
        for (int column_id=t_vec_vec[0].size()+1;(uint64_t)column_id<temp_data[row_id].size();column_id++)
        {
            double rel_eb=stod(temp_data[row_id][0]);
            vector<double> t_vec;
            for (int i=0;i<(int)t_vec_vec[0].size();i++)
                t_vec.push_back(stod(temp_data[row_id][i+1]));
            string value_name=temp_data[0][column_id];
            double value=stod(temp_data[row_id][column_id]);
            data[csv_path][rel_eb][t_vec][value_name]=value;
        }
        for (double rel_eb:rel_eb_vec)
        for (const auto &t_vec:t_vec_vec)
        for (string metric:{"BR","PSNR"})
        {
            auto &values=data[csv_path][rel_eb][t_vec];
            if (!values.contains(metric)||!isfinite(values[metric]))
                throw runtime_error("missing or nonfinite "+metric+" in "+csv_path);
        }
    }

    printf("第一轮 对每个stencil pattern和traversal order计算平均BR和PSNR。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> avg_br_1,avg_psnr_1;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        for (auto &traversal_order:traversal_order_vec)
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            avg_br_1[rel_eb][predictor_name][traversal_order]+=data[csv_path][rel_eb][t_vec]["BR"];
            avg_psnr_1[rel_eb][predictor_name][traversal_order]+=data[csv_path][rel_eb][t_vec]["PSNR"];
        }
    for (auto &rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        avg_br_1[rel_eb][predictor_name][traversal_order]/=(t_vec_vec.size());
        avg_psnr_1[rel_eb][predictor_name][traversal_order]/=(t_vec_vec.size());
    }

    printf("第一轮 计算平均斜率。。。。。。\n");
    // 访问方式是slope_1[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> slope_1;
    unordered_map<double,unordered_map<string,unordered_map<string,bool>>> equal_rate_1;
    for (auto &rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        double left_rel_eb,right_rel_eb;
        if (rel_eb==rel_eb_vec[0])
            left_rel_eb=rel_eb;
        else
            left_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)-1);
        if (rel_eb==rel_eb_vec.back())
            right_rel_eb=rel_eb;
        else
            right_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)+1);
        double delta_br=avg_br_1[right_rel_eb][predictor_name][traversal_order]-avg_br_1[left_rel_eb][predictor_name][traversal_order];
        double delta_psnr=avg_psnr_1[right_rel_eb][predictor_name][traversal_order]-avg_psnr_1[left_rel_eb][predictor_name][traversal_order];
        if (delta_br==0)
        {
            string path=csv_prefix+"_"+predictor_name+"_"+traversal_order+".csv";
            double common_br=data[path][rel_eb][t_vec_vec[0]]["BR"];
            bool equal_rates=all_of(t_vec_vec.begin(),t_vec_vec.end(),[&](const vector<double> &parameters){return data[path][rel_eb][parameters]["BR"]==common_br;});
            if (!equal_rates)
                throw runtime_error("zero bitrate span in coefficient-selection slope");
            equal_rate_1[rel_eb][predictor_name][traversal_order]=true;
            slope_1[rel_eb][predictor_name][traversal_order]=numeric_limits<double>::quiet_NaN();
            fprintf(stderr,"equal-rate coefficient candidates: %s %s rel_eb=%.17g; rank by PSNR (slope undefined)\n",predictor_name.c_str(),traversal_order.c_str(),rel_eb);
        }
        else
            slope_1[rel_eb][predictor_name][traversal_order]=delta_psnr/delta_br;
    }

    printf("第一轮 计算每个点的分数。。。。。。\n");
    // 访问方式是score_1[rel_eb][predictor_name][traversal_order][t_vec]
    unordered_map<double,unordered_map<string,unordered_map<string,unordered_map<vector<double>,double>>>> score_1;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        for (auto &traversal_order:traversal_order_vec)    
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            double temp_slope=slope_1[rel_eb][predictor_name][traversal_order];
            double &temp_score=score_1[rel_eb][predictor_name][traversal_order][t_vec];
            double temp_br=data[csv_path][rel_eb][t_vec]["BR"];
            double temp_psnr=data[csv_path][rel_eb][t_vec]["PSNR"];
            temp_score=equal_rate_1[rel_eb][predictor_name][traversal_order]?temp_psnr:(-temp_slope*temp_br+temp_psnr)/sqrt(temp_slope*temp_slope+1);
        }

    printf("第一轮 寻找每个rel_eb、traversal order、stencil pattern下的最好情况。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,vector<double>>>> best_t_vec;
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> best_score_1;
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> best_br_1;
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> best_psnr_1;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
        best_score_1[rel_eb][predictor_name][traversal_order]=-1e10;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t_vec:t_vec_vec)
        for (auto &predictor_name:predictor_name_vec)
        for (auto &traversal_order:traversal_order_vec)
        {
            if ((csv_path.find(predictor_name)==string::npos) || (csv_path.find(traversal_order)==string::npos))
                continue;
            if (best_score_1[rel_eb][predictor_name][traversal_order]<score_1[rel_eb][predictor_name][traversal_order][t_vec])
            {
                best_score_1[rel_eb][predictor_name][traversal_order]=score_1[rel_eb][predictor_name][traversal_order][t_vec];
                best_t_vec[rel_eb][predictor_name][traversal_order]=t_vec;
                best_br_1[rel_eb][predictor_name][traversal_order]=data[csv_path][rel_eb][t_vec]["BR"];
                best_psnr_1[rel_eb][predictor_name][traversal_order]=data[csv_path][rel_eb][t_vec]["PSNR"];
            }
        }
    
    printf("第二轮 对每个stencil pattern计算平均BR和PSNR。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,double>> avg_br_2,avg_psnr_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        avg_br_2[rel_eb][predictor_name]+=best_br_1[rel_eb][predictor_name][traversal_order];
        avg_psnr_2[rel_eb][predictor_name]+=best_psnr_1[rel_eb][predictor_name][traversal_order];
    }
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        avg_br_2[rel_eb][predictor_name]/=(traversal_order_vec.size());
        avg_psnr_2[rel_eb][predictor_name]/=(traversal_order_vec.size());
    }

    printf("第二轮 计算平均斜率。。。。。。\n");
    // 访问方式是slope_2[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,double>> slope_2;
    unordered_map<double,unordered_map<string,bool>> equal_rate_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        double left_rel_eb,right_rel_eb;
        if (rel_eb==rel_eb_vec[0])
            left_rel_eb=rel_eb;
        else
            left_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)-1);
        if (rel_eb==rel_eb_vec.back())
            right_rel_eb=rel_eb;
        else
            right_rel_eb=*(find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb)+1);
        double delta_br=avg_br_2[right_rel_eb][predictor_name]-avg_br_2[left_rel_eb][predictor_name];
        double delta_psnr=avg_psnr_2[right_rel_eb][predictor_name]-avg_psnr_2[left_rel_eb][predictor_name];
        if (delta_br==0)
        {
            double common_br=best_br_1[rel_eb][predictor_name][traversal_order_vec[0]];
            bool equal_rates=all_of(traversal_order_vec.begin(),traversal_order_vec.end(),[&](const string &order){return best_br_1[rel_eb][predictor_name][order]==common_br;});
            if (!equal_rates)
                throw runtime_error("zero bitrate span in traversal-selection slope");
            equal_rate_2[rel_eb][predictor_name]=true;
            slope_2[rel_eb][predictor_name]=numeric_limits<double>::quiet_NaN();
            fprintf(stderr,"equal-rate traversal candidates: %s rel_eb=%.17g; rank by PSNR (slope undefined)\n",predictor_name.c_str(),rel_eb);
        }
        else
            slope_2[rel_eb][predictor_name]=delta_psnr/delta_br;
    }

    printf("第二轮 计算每个点的分数。。。。。。\n");
    // 访问方式是score_2[rel_eb][predictor_name][traversal_order]
    unordered_map<double,unordered_map<string,unordered_map<string,double>>> score_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        double temp_slope=slope_2[rel_eb][predictor_name];
        double &temp_score=score_2[rel_eb][predictor_name][traversal_order];
        double temp_br=best_br_1[rel_eb][predictor_name][traversal_order];
        double temp_psnr=best_psnr_1[rel_eb][predictor_name][traversal_order];
        temp_score=equal_rate_2[rel_eb][predictor_name]?temp_psnr:(-temp_slope*temp_br+temp_psnr)/sqrt(temp_slope*temp_slope+1);
    }

    printf("第二轮 寻找每个rel_eb、stencil pattern下的最好情况。。。。。。\n");
    // 访问方式是xxx[rel_eb][predictor_name]
    unordered_map<double,unordered_map<string,string>> best_traversal_order;
    unordered_map<double,unordered_map<string,double>> best_score_2;
    unordered_map<double,unordered_map<string,double>> best_br_2;
    unordered_map<double,unordered_map<string,double>> best_psnr_2;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
        best_score_2[rel_eb][predictor_name]=-1e10;
    for (auto rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    for (auto &traversal_order:traversal_order_vec)
    {
        if (best_score_2[rel_eb][predictor_name]<score_2[rel_eb][predictor_name][traversal_order])
        {
            best_score_2[rel_eb][predictor_name]=score_2[rel_eb][predictor_name][traversal_order];
            best_traversal_order[rel_eb][predictor_name]=traversal_order;
            best_br_2[rel_eb][predictor_name]=best_br_1[rel_eb][predictor_name][traversal_order];
            best_psnr_2[rel_eb][predictor_name]=best_psnr_1[rel_eb][predictor_name][traversal_order];
        }
    }

    printf("输出结果。。。。。。\n");
    auto parent=filesystem::path(output_csv_path).parent_path();
    if (!parent.empty())
        filesystem::create_directories(parent);
    create_csv_header(output_csv_path,"rel_eb");
    for (auto &rel_eb:rel_eb_vec)
    for (auto &predictor_name:predictor_name_vec)
    {
        string br_name=predictor_name+"_BR";
        string psnr_name=predictor_name+"_PSNR";
        write_csv_item(output_csv_path,rel_eb,br_name,best_br_2[rel_eb][predictor_name]);
        write_csv_item(output_csv_path,rel_eb,psnr_name,best_psnr_2[rel_eb][predictor_name]);
        const auto &order=best_traversal_order[rel_eb][predictor_name];
        write_csv_item(output_csv_path,rel_eb,predictor_name+"_traversal_order",order);
        for (uint64_t parameter=0;parameter<t_vec_vec[0].size();parameter++)
            write_csv_item(output_csv_path,rel_eb,predictor_name+"_t"+to_string(parameter+1),best_t_vec[rel_eb][predictor_name][order][parameter]);
        write_csv_item(output_csv_path,rel_eb,predictor_name+"_coefficient_slope",slope_1[rel_eb][predictor_name][order]);
        write_csv_item(output_csv_path,rel_eb,predictor_name+"_coefficient_score_kind",string(equal_rate_1[rel_eb][predictor_name][order]?"equal_rate_psnr":"tangent"));
        write_csv_item(output_csv_path,rel_eb,predictor_name+"_traversal_slope",slope_2[rel_eb][predictor_name]);
        write_csv_item(output_csv_path,rel_eb,predictor_name+"_traversal_score_kind",string(equal_rate_2[rel_eb][predictor_name]?"equal_rate_psnr":"tangent"));
        write_csv_item(output_csv_path,rel_eb,predictor_name+"_score",best_score_2[rel_eb][predictor_name]);
    }
    return 0;
}
catch (const exception &error)
{
    fprintf(stderr,"error: %s\n",error.what());
    return 1;
}
