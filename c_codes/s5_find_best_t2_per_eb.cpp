// 从不同csv文件读取BR和H
// 对每个stencil pattern、每个eb单独排序t2
// 计算每个stencil pattern、每个eb使用不同估计值时的tau
// 选择每个stencil pattern、每个eb的最好t2
// 对每个eb排序stencil pattern，计算tau

#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <unordered_map>

#include "csv_tools/csv.hpp"

using namespace std;

inline void hash_combine(uint64_t &v1,uint64_t v2) //输入需要std::hash产生的uint64_t
{
    v1^=v2+0x9e3779b97f4a7c15ULL+(v1<<6)+(v1>>2);
}

namespace std
{
    template<>
    struct hash<tuple<double,double>>
    {
        size_t operator()(const tuple<double,double> &t) const
        {
            auto[a,b]=t;
            uint64_t h=0;
            hash_combine(h,hash<double>{}(a));
            hash_combine(h,hash<double>{}(b));
            return h;
        }
    };

    template<>
    struct hash<tuple<double,double,double>>
    {
        size_t operator()(const tuple<double,double,double> &t) const
        {
            auto[a,b,c]=t;
            uint64_t h=0;
            hash_combine(h,hash<double>{}(a));
            hash_combine(h,hash<double>{}(b));
            hash_combine(h,hash<double>{}(c));
            return h;
        }
    };

    template<>
    struct hash<tuple<string,string>>
    {
        size_t operator()(const tuple<string,string> &t) const
        {
            auto[a,b]=t;
            uint64_t h=0;
            hash_combine(h,hash<string>{}(a));
            hash_combine(h,hash<string>{}(b));
            return h;
        }
    };
}

void get_average_slope(double &slope,bool &slope_infinite,bool &slope_undefined,unordered_map<tuple<double,double>,double> &br,
    unordered_map<tuple<double,double>,double> &psnr,double rel_eb,vector<double> &rel_eb_vec,vector<double> &t2_vec)
{
    auto rel_eb_it=find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb);
    auto rel_eb_prev_it=rel_eb_it;
    auto rel_eb_next_it=rel_eb_it;
    if (rel_eb_prev_it!=rel_eb_vec.begin())
        rel_eb_prev_it--;
    if (rel_eb_next_it!=rel_eb_vec.end()-1)
        rel_eb_next_it++;
    
    int valid_slope_num=0;
    double avg_angle=0;
    for (auto &t2:t2_vec)
    {
        if (*rel_eb_prev_it<*rel_eb_next_it)
            if ((br[{*rel_eb_prev_it,t2}]<br[{*rel_eb_next_it,t2}]) || (psnr[{*rel_eb_prev_it,t2}]<psnr[{*rel_eb_next_it,t2}]))
                continue;
        if (*rel_eb_prev_it>*rel_eb_next_it)
            if ((br[{*rel_eb_prev_it,t2}]>br[{*rel_eb_next_it,t2}]) || (psnr[{*rel_eb_prev_it,t2}]>psnr[{*rel_eb_next_it,t2}]))
                continue;
        if (br[{*rel_eb_prev_it,t2}]==br[{*rel_eb_next_it,t2}])
            if (psnr[{*rel_eb_prev_it,t2}]==psnr[{*rel_eb_next_it,t2}])
                continue;
            else
            {
                avg_angle+=M_PI/2;
                valid_slope_num++;
            }
        else
        {
            double slope=(psnr[{*rel_eb_next_it,t2}]-psnr[{*rel_eb_prev_it,t2}])/(br[{*rel_eb_next_it,t2}]-br[{*rel_eb_prev_it,t2}]);
            avg_angle+=atan(slope);
            valid_slope_num++;
        }
    }
    if (valid_slope_num==0)
        throw runtime_error("valid_slope_num==0");
    else
    {
        slope_undefined=false;
        avg_angle/=valid_slope_num;
        if (avg_angle==M_PI/2)
        {
            slope=0;
            slope_infinite=true;
        }
        else
        {
            slope=tan(avg_angle);
            slope_infinite=false;
        }
    }
}

double calc_tau(unordered_map<tuple<double,double>,double> &dist_br,unordered_map<tuple<double,double>,double> &dist_h,double rel_eb,vector<double> &t2_vec)
{
    int64_t tau=0;
    for (auto t2_base:t2_vec)
    for (auto t2_oppo:t2_vec)
    {
        if (t2_base==t2_oppo)
            continue;
        double delta=(dist_br[{rel_eb,t2_oppo}]-dist_br[{rel_eb,t2_base}])*(dist_h[{rel_eb,t2_oppo}]-dist_h[{rel_eb,t2_base}]);
        if (delta>0)
            tau++;
        if (delta<0)
            tau--;
    }
    return (double)tau/(t2_vec.size()*(t2_vec.size()-1));
}

double find_best_t2(unordered_map<tuple<double,double>,double> &dist,double rel_eb,vector<double> &t2_vec)
{
    double best_t2=t2_vec[0];
    for (auto t2:t2_vec)
    {
        if (t2==best_t2)
            continue;
        if (dist[{rel_eb,t2}]>dist[{rel_eb,best_t2}])
            best_t2=t2;
    }
    return best_t2;
}

void get_average_slope_2(double &slope,bool &slope_infinite,bool &slope_undefined,unordered_map<string,unordered_map<tuple<double,double>,double>> &br,
    unordered_map<string,unordered_map<tuple<double,double>,double>> &psnr,unordered_map<string,unordered_map<double,double>> &best_t2,double rel_eb,
    vector<double> &rel_eb_vec,vector<string> &csv_path_vec)
{
    auto rel_eb_it=find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb);
    auto rel_eb_prev_it=rel_eb_it;
    auto rel_eb_next_it=rel_eb_it;
    if (rel_eb_prev_it!=rel_eb_vec.begin())
        rel_eb_prev_it--;
    if (rel_eb_next_it!=rel_eb_vec.end()-1)
        rel_eb_next_it++;
    
    int valid_slope_num=0;
    double avg_angle=0;
    for (auto &csv_path:csv_path_vec)
    {
        double t2=best_t2[csv_path][rel_eb];
        if (*rel_eb_prev_it<*rel_eb_next_it) 
            if ((br[csv_path][{*rel_eb_prev_it,t2}]<br[csv_path][{*rel_eb_next_it,t2}]) || (psnr[csv_path][{*rel_eb_prev_it,t2}]<psnr[csv_path][{*rel_eb_next_it,t2}]))
            {
                printf("csv_path=%s, rel_eb=%f, t2=%f, skip for slope calc since it's not monotone\n",csv_path.c_str(),rel_eb,t2);
                continue;
            }
        if (*rel_eb_prev_it>*rel_eb_next_it)
            if ((br[csv_path][{*rel_eb_prev_it,t2}]>br[csv_path][{*rel_eb_next_it,t2}]) || (psnr[csv_path][{*rel_eb_prev_it,t2}]>psnr[csv_path][{*rel_eb_next_it,t2}]))
            {
                printf("csv_path=%s, rel_eb=%f, t2=%f, skip for slope calc since it's not monotone\n",csv_path.c_str(),rel_eb,t2);
                continue;
            }
        if (br[csv_path][{*rel_eb_prev_it,t2}]==br[csv_path][{*rel_eb_next_it,t2}])
            if (psnr[csv_path][{*rel_eb_prev_it,t2}]==psnr[csv_path][{*rel_eb_next_it,t2}])
                continue;
            else
            {
                avg_angle+=M_PI/2;
                valid_slope_num++;
            }
        else
        {
            double slope=(psnr[csv_path][{*rel_eb_next_it,t2}]-psnr[csv_path][{*rel_eb_prev_it,t2}]);
            slope/=(br[csv_path][{*rel_eb_next_it,t2}]-br[csv_path][{*rel_eb_prev_it,t2}]);
            avg_angle+=atan(slope);
            valid_slope_num++;
        }
    }
    if (valid_slope_num==0)
        throw runtime_error("valid_slope_num==0");
    else
    {
        slope_undefined=false;
        avg_angle/=valid_slope_num;
        if (avg_angle==M_PI/2)
        {
            slope=0;
            slope_infinite=true;
        }
        else
        {
            slope=tan(avg_angle);
            slope_infinite=false;
        }
    }
}

double get_dist_2(unordered_map<string,unordered_map<tuple<double,double>,double>> &br,unordered_map<string,unordered_map<tuple<double,double>,double>> &psnr,
    unordered_map<string,unordered_map<double,double>> &best_t2,double rel_eb,vector<double> &rel_eb_vec,string csv_path_base,string csv_path_oppo)
{
    auto rel_eb_it=find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb);
    auto rel_eb_prev_it=rel_eb_it;
    auto rel_eb_next_it=rel_eb_it;
    if (rel_eb_prev_it!=rel_eb_vec.begin())
        rel_eb_prev_it--;
    if (rel_eb_next_it!=rel_eb_vec.end()-1)
        rel_eb_next_it++;
    double &t2_base=best_t2[csv_path_base][rel_eb];
    double &t2_oppo=best_t2[csv_path_oppo][rel_eb];
    if (psnr[csv_path_base][{*rel_eb_next_it,t2_base}]==psnr[csv_path_base][{*rel_eb_prev_it,t2_base}])
        if (br[csv_path_base][{*rel_eb_next_it,t2_base}]==br[csv_path_base][{*rel_eb_prev_it,t2_base}])
            return -br[csv_path_oppo][{rel_eb,t2_oppo}]+br[csv_path_base][{rel_eb,t2_base}];
        else
            return psnr[csv_path_oppo][{rel_eb,t2_oppo}]-psnr[csv_path_base][{rel_eb,t2_base}];
    else 
        if (br[csv_path_base][{*rel_eb_next_it,t2_base}]==br[csv_path_base][{*rel_eb_prev_it,t2_base}])
            return -br[csv_path_oppo][{rel_eb,t2_oppo}]+br[csv_path_base][{rel_eb,t2_base}];
        else
        {
            double slope=(psnr[csv_path_base][{*rel_eb_next_it,t2_base}]-psnr[csv_path_base][{*rel_eb_prev_it,t2_base}]);
            slope/=(br[csv_path_base][{*rel_eb_next_it,t2_base}]-br[csv_path_base][{*rel_eb_prev_it,t2_base}]);
            double dist=-slope*(br[csv_path_oppo][{rel_eb,t2_oppo}]-br[csv_path_base][{rel_eb,t2_base}]);
            dist+=(psnr[csv_path_oppo][{rel_eb,t2_oppo}]-psnr[csv_path_base][{rel_eb,t2_base}]);
            return dist;
        }
}

double calc_tau_2(unordered_map<double,unordered_map<string,double>> &dist_2_br,unordered_map<double,unordered_map<string,double>> &dist_2_h,
    double rel_eb,vector<string> &csv_path_vec)
{
    int64_t tau=0;
    for (auto csv_path_base:csv_path_vec)
    for (auto csv_path_oppo:csv_path_vec)
    {
        if (csv_path_base==csv_path_oppo)
            continue;
        double delta=(dist_2_br[rel_eb][csv_path_oppo]-dist_2_br[rel_eb][csv_path_base])*(dist_2_h[rel_eb][csv_path_oppo]-dist_2_h[rel_eb][csv_path_base]);
        if (delta>0)
            tau++;
        if (delta<0)
            tau--;
    }
    return (double)tau/(csv_path_vec.size()*(csv_path_vec.size()-1));
}

string find_best_sp(unordered_map<string,double> &dist_2,vector<string> &csv_path_vec)
{
    string best_sp=csv_path_vec[0];
    for (auto &csv_path:csv_path_vec)
    {
        if (csv_path==best_sp)
            continue;
        if (dist_2[csv_path]>dist_2[best_sp])
            best_sp=csv_path;
    }
    return best_sp;
}

int main()
{
    vector<string> csv_path_vec;
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi01_120.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi01_021.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi01_012.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi02_120.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi02_021.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi02_012.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi12_120.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi12_021.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/CLDICE_center_multi12_012.csv");
    vector<double> rel_eb_vec;
    read_all_values_in_column(csv_path_vec[0],"rel_eb",rel_eb_vec);
    vector<double> t2_vec;
    read_all_values_in_column(csv_path_vec[0],"t2",t2_vec);

    vector<string> aspt_name_vec={"BR"};//第一个是标准值
    string standard_psnr_name="PSNR";
    string aspt_psnr_name="PSNR";

    unordered_map<string,unordered_map<tuple<double,double>,double>> standard_psnr,aspt_psnr;
    vector<unordered_map<string,unordered_map<tuple<double,double>,double>>> aspt_vec(aspt_name_vec.size());
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t2:t2_vec)
    {
        for (size_t i=0;i<aspt_name_vec.size();i++)
            aspt_vec[i][csv_path][{rel_eb,t2}]=read_value(csv_path,rel_eb,t2,aspt_name_vec[i]);
        standard_psnr[csv_path][{rel_eb,t2}]=read_value(csv_path,rel_eb,t2,standard_psnr_name);
        aspt_psnr[csv_path][{rel_eb,t2}]=read_value(csv_path,rel_eb,t2,aspt_psnr_name);
    }
    
    // 对每个stencil pattern、每个eb，获取每个t2相对于平均斜率的dist
    vector<unordered_map<string,unordered_map<tuple<double,double>,double>>> dist_vec(aspt_name_vec.size());
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (size_t i=0;i<aspt_name_vec.size();i++)
    {
        double slope;
        bool slope_infinite,slope_undefined;
        if (i==0)
            get_average_slope(slope,slope_infinite,slope_undefined,aspt_vec[i][csv_path],standard_psnr[csv_path],rel_eb,rel_eb_vec,t2_vec);
        else
            get_average_slope(slope,slope_infinite,slope_undefined,aspt_vec[i][csv_path],aspt_psnr[csv_path],rel_eb,rel_eb_vec,t2_vec);
        for (auto &t2:t2_vec)
            if (i==0)
                if (slope_infinite)
                    dist_vec[i][csv_path][{rel_eb,t2}]=-aspt_vec[i][csv_path][{rel_eb,t2}];
                else
                    dist_vec[i][csv_path][{rel_eb,t2}]=(-slope*aspt_vec[i][csv_path][{rel_eb,t2}]+standard_psnr[csv_path][{rel_eb,t2}])/sqrt(slope*slope+1);
            else
                if (slope_infinite)
                    dist_vec[i][csv_path][{rel_eb,t2}]=-aspt_vec[i][csv_path][{rel_eb,t2}];
                else
                    dist_vec[i][csv_path][{rel_eb,t2}]=(-slope*aspt_vec[i][csv_path][{rel_eb,t2}]+aspt_psnr[csv_path][{rel_eb,t2}])/sqrt(slope*slope+1);
    }

    // 对每个stencil pattern、每个eb，计算对t2的排序的tau
    for (auto &csv_path:csv_path_vec)
    {
        printf("csv_path=%s\n",csv_path.c_str());
        for (auto &rel_eb:rel_eb_vec)
        {
            vector<double> aspt_tau_vec(aspt_name_vec.size());
            for (size_t i=1;i<aspt_name_vec.size();i++)
                aspt_tau_vec[i]=calc_tau(dist_vec[0][csv_path],dist_vec[i][csv_path],rel_eb,t2_vec);
            double best_aspt_tau=-1;
            size_t best_aspt_i=0;
            printf("rel_eb=%f, ",rel_eb);
            for (size_t i=1;i<aspt_name_vec.size();i++)
            {
                printf("%s tau=%f, ",aspt_name_vec[i].c_str(),aspt_tau_vec[i]);
                if (aspt_tau_vec[i]>best_aspt_tau)
                {
                    best_aspt_tau=aspt_tau_vec[i];
                    best_aspt_i=i;
                }
            }
            printf("best aspt=%s\n",aspt_name_vec[best_aspt_i].c_str());
        }
        printf("\n");
    }

    // 对每个stencil pattern、每个eb，选择最好的t2
    vector<unordered_map<string,unordered_map<double,double>>> best_t2_vec(aspt_name_vec.size());
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (size_t i=0;i<aspt_name_vec.size();i++)
    {
        best_t2_vec[i][csv_path][rel_eb]=find_best_t2(dist_vec[i][csv_path],rel_eb,t2_vec);
        printf("csv_path=%s, rel_eb=%f, aspt=%s, best_t2=%f\n",csv_path.c_str(),rel_eb,aspt_name_vec[i].c_str(),best_t2_vec[i][csv_path][rel_eb]);
    }

    // 对每个eb，计算使用不同stencil pattern时的dist，使用最好的t2
    vector<unordered_map<double,unordered_map<string,double>>> dist_2_vec(aspt_name_vec.size());
    for (auto &rel_eb:rel_eb_vec)
    for (size_t i=0;i<aspt_name_vec.size();i++)
    {
        double slope;
        bool slope_infinite,slope_undefined;
        if (i==0)
            get_average_slope_2(slope,slope_infinite,slope_undefined,aspt_vec[i],standard_psnr,best_t2_vec[i],rel_eb,rel_eb_vec,csv_path_vec);
        else
            get_average_slope_2(slope,slope_infinite,slope_undefined,aspt_vec[i],aspt_psnr,best_t2_vec[i],rel_eb,rel_eb_vec,csv_path_vec);
        for (auto &csv_path:csv_path_vec)
            if (i==0)
                if (slope_infinite)
                    dist_2_vec[i][rel_eb][csv_path]=-aspt_vec[i][csv_path][{rel_eb,best_t2_vec[i][csv_path][rel_eb]}];
                else
                {
                    dist_2_vec[i][rel_eb][csv_path]=-slope*aspt_vec[i][csv_path][{rel_eb,best_t2_vec[i][csv_path][rel_eb]}];
                    dist_2_vec[i][rel_eb][csv_path]+=standard_psnr[csv_path][{rel_eb,best_t2_vec[i][csv_path][rel_eb]}];
                    dist_2_vec[i][rel_eb][csv_path]/=sqrt(slope*slope+1);
                }
            else
                if (slope_infinite)
                    dist_2_vec[i][rel_eb][csv_path]=-aspt_vec[i][csv_path][{rel_eb,best_t2_vec[i][csv_path][rel_eb]}];
                else
                {
                    dist_2_vec[i][rel_eb][csv_path]=-slope*aspt_vec[i][csv_path][{rel_eb,best_t2_vec[i][csv_path][rel_eb]}];
                    dist_2_vec[i][rel_eb][csv_path]+=aspt_psnr[csv_path][{rel_eb,best_t2_vec[i][csv_path][rel_eb]}];
                    dist_2_vec[i][rel_eb][csv_path]/=sqrt(slope*slope+1);
                }
    }

    // 对每个eb，计算使用不同stencil pattern时的tau
    for (auto &rel_eb:rel_eb_vec)
    {
        vector<double> aspt_tau_vec(aspt_name_vec.size());
        for (size_t i=1;i<aspt_name_vec.size();i++)
            aspt_tau_vec[i]=calc_tau_2(dist_2_vec[0],dist_2_vec[i],rel_eb,csv_path_vec);
        double best_aspt_tau=-1;
        size_t best_aspt_i=0;
        printf("rel_eb=%f, ",rel_eb);
        for (size_t i=1;i<aspt_name_vec.size();i++)
        {
            printf("%s tau=%f, ",aspt_name_vec[i].c_str(),aspt_tau_vec[i]);
            if (aspt_tau_vec[i]>best_aspt_tau)            
            {
                best_aspt_tau=aspt_tau_vec[i];
                best_aspt_i=i;
            }
        }
        printf("best aspt=%s\n",aspt_name_vec[best_aspt_i].c_str());
    }

    // 对每个eb，选择最好的stencil pattern，使用最好的t2
    vector<unordered_map<double,string>> best_sp_vec(aspt_name_vec.size());
    for (auto &rel_eb:rel_eb_vec)
    for (size_t i=0;i<aspt_name_vec.size();i++)
    {
        best_sp_vec[i][rel_eb]=find_best_sp(dist_2_vec[i][rel_eb],csv_path_vec);
        printf("rel_eb=%f, aspt=%s, best_sp=%s, best_t2=%f\n",rel_eb,aspt_name_vec[i].c_str(),best_sp_vec[i][rel_eb].c_str(),
            best_t2_vec[i][best_sp_vec[i][rel_eb]][rel_eb]);
    }

    // 对每个eb，每个预测方向，选择最好的遍历顺序，使用最好的t2
    for (auto &rel_eb:rel_eb_vec)
    {
        for (const string &sp:{"multi01","multi02","multi12"})
        {
            vector<string> temp_csv_path_vec;
            for (auto &csv_path:csv_path_vec)
                if (csv_path.find(sp)!=string::npos)
                    temp_csv_path_vec.push_back(csv_path);
            string best_csv_path=find_best_sp(dist_2_vec[0][rel_eb],temp_csv_path_vec);
            printf("%f %f ",aspt_vec[0][best_csv_path][{rel_eb,best_t2_vec[0][best_csv_path][rel_eb]}],standard_psnr[best_csv_path][{rel_eb,best_t2_vec[0][best_csv_path][rel_eb]}]);
        }
        printf("\n");
    }
}