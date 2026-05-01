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

double get_dist(unordered_map<tuple<double,double>,double> &br,unordered_map<tuple<double,double>,double> &psnr,
    vector<double> &rel_eb_vec,double rel_eb,double t2_base,double t2_oppo)
{
    auto rel_eb_it=find(rel_eb_vec.begin(),rel_eb_vec.end(),rel_eb);
    auto rel_eb_prev_it=rel_eb_it;
    auto rel_eb_next_it=rel_eb_it;
    if (rel_eb_prev_it!=rel_eb_vec.begin())
        rel_eb_prev_it--;
    if (rel_eb_next_it!=rel_eb_vec.end()-1)
        rel_eb_next_it++;
    double slope=(psnr[{*rel_eb_next_it,t2_base}]-psnr[{*rel_eb_prev_it,t2_base}])/(br[{*rel_eb_next_it,t2_base}]-br[{*rel_eb_prev_it,t2_base}]);
    return -slope*(br[{rel_eb,t2_oppo}]-br[{rel_eb,t2_base}])+(psnr[{rel_eb,t2_oppo}]-psnr[{rel_eb,t2_base}]);
}

double calc_tau(unordered_map<tuple<double,double,double>,double> &dist_br,unordered_map<tuple<double,double,double>,double> &dist_h,double rel_eb,vector<double> &t2_vec)
{
    int64_t tau=0;
    for (auto t2_base:t2_vec)
    for (auto t2_oppo:t2_vec)
    {
        if (t2_base==t2_oppo)
            continue;
        if (dist_br[{rel_eb,t2_base,t2_oppo}]*dist_h[{rel_eb,t2_base,t2_oppo}]>0)
            tau++;
        else if (dist_br[{rel_eb,t2_base,t2_oppo}]*dist_h[{rel_eb,t2_base,t2_oppo}]<0)
            tau--;
    }
    return (double)tau/(t2_vec.size()*(t2_vec.size()-1));
}

double find_best_t2(unordered_map<tuple<double,double,double>,double> &dist,double rel_eb,vector<double> &t2_vec)
{
    double best_t2=t2_vec[0];
    int best_win_num=0;
    for (auto t2_oppo:t2_vec)
    {
        if (t2_oppo==best_t2)
            continue;
        if (dist[{rel_eb,best_t2,t2_oppo}]<0)
            best_win_num++;
        if (dist[{rel_eb,t2_oppo,best_t2}]>0)
            best_win_num++;
    }
    for (auto t2:t2_vec)
    {
        if (t2==best_t2)
            continue;
        int win_num=0;
        for (auto t2_oppo:t2_vec)
        {
            if (t2_oppo==t2)
                continue;
            if (dist[{rel_eb,t2,t2_oppo}]<0)
                win_num++;
            if (dist[{rel_eb,t2_oppo,t2}]>0)
                win_num++;
        }
        if (win_num>best_win_num)
        {
            best_win_num=win_num;
            best_t2=t2;
        }
    }
    return best_t2;
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
    double slope=(psnr[csv_path_base][{*rel_eb_next_it,t2_base}]-psnr[csv_path_base][{*rel_eb_prev_it,t2_base}]);
    slope/=(br[csv_path_base][{*rel_eb_next_it,t2_base}]-br[csv_path_base][{*rel_eb_prev_it,t2_base}]);
    return -slope*(br[csv_path_oppo][{rel_eb,t2_oppo}]-br[csv_path_base][{rel_eb,t2_base}])+(psnr[csv_path_oppo][{rel_eb,t2_oppo}]-psnr[csv_path_base][{rel_eb,t2_base}]);
}

double calc_tau_2(unordered_map<double,unordered_map<tuple<string,string>,double>> &dist_2_br,unordered_map<double,unordered_map<tuple<string,string>,double>> &dist_2_h,
    double rel_eb,vector<string> &csv_path_vec)
{
    int64_t tau=0;
    for (auto csv_path_base:csv_path_vec)
    for (auto csv_path_oppo:csv_path_vec)
    {
        if (csv_path_base==csv_path_oppo)
            continue;
        if (dist_2_br[rel_eb][{csv_path_base,csv_path_oppo}]*dist_2_h[rel_eb][{csv_path_base,csv_path_oppo}]>0)
            tau++;
        else if (dist_2_br[rel_eb][{csv_path_base,csv_path_oppo}]*dist_2_h[rel_eb][{csv_path_base,csv_path_oppo}]<0)
            tau--;
    }
    return (double)tau/(csv_path_vec.size()*(csv_path_vec.size()-1));
}

string find_best_sp(unordered_map<tuple<string,string>,double> &dist_2,vector<string> &csv_path_vec)
{
    string best_csv_path=csv_path_vec[0];
    int best_win_num=0;
    for (auto csv_path_oppo:csv_path_vec)
    {
        if (csv_path_oppo==best_csv_path)
            continue;
        if (dist_2[{best_csv_path,csv_path_oppo}]<0)
            best_win_num++;
        if (dist_2[{csv_path_oppo,best_csv_path}]>0)
            best_win_num++;
    }
    for (auto csv_path:csv_path_vec)
    {
        if (csv_path==best_csv_path)
            continue;
        int win_num=0;
        for (auto csv_path_oppo:csv_path_vec)
        {
            if (csv_path_oppo==csv_path)
                continue;
            if (dist_2[{csv_path,csv_path_oppo}]<0)
                win_num++;
            if (dist_2[{csv_path_oppo,csv_path}]>0)
                win_num++;
        }
        if (win_num>best_win_num)
        {
            best_win_num=win_num;
            best_csv_path=csv_path;
        }
    }
    return best_csv_path;
}

int main()
{
    vector<string> csv_path_vec;
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic0_120.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic0_021.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic0_012.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic1_120.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic1_021.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic1_012.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic2_120.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic2_021.csv");
    csv_path_vec.push_back("/home/x-zjian1/ASTZ_tests/csv/cubic_Miranda_cubic2_012.csv");
    vector<double> rel_eb_vec;
    read_all_values_in_column(csv_path_vec[0],"rel_eb",rel_eb_vec);
    vector<double> t2_vec;
    read_all_values_in_column(csv_path_vec[0],"t2",t2_vec);

    vector<string> aspt_name_vec={"BR","BR_s16","H1_s16","H2_s16"};//第一个是标准值
    string standard_psnr_name="PSNR";
    string aspt_psnr_name="PSNR_s16";

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
    
    // 对每个stencil pattern、每个eb，获取每对t2之间的dist
    unordered_map<string,unordered_map<string,unordered_map<tuple<double,double,double>,double>>> dist_vec;
    for (auto &csv_path:csv_path_vec)
    for (auto &rel_eb:rel_eb_vec)
    for (auto &t2_base:t2_vec)
    for (auto &t2_oppo:t2_vec)
    for (size_t i=0;i<aspt_name_vec.size();i++)
        if (i==0)
            dist_vec[aspt_name_vec[i]][csv_path][{rel_eb,t2_base,t2_oppo}]=get_dist(aspt_vec[i][csv_path],standard_psnr[csv_path],rel_eb_vec,rel_eb,t2_base,t2_oppo);
        else
            dist_vec[aspt_name_vec[i]][csv_path][{rel_eb,t2_base,t2_oppo}]=get_dist(aspt_vec[i][csv_path],aspt_psnr[csv_path],rel_eb_vec,rel_eb,t2_base,t2_oppo);
    
    // 对每个stencil pattern、每个eb，计算对t2的排序的tau
    for (auto &csv_path:csv_path_vec)
    {
        printf("csv_path=%s\n",csv_path.c_str());
        for (auto &rel_eb:rel_eb_vec)
        {
            vector<double> aspt_tau_vec(aspt_name_vec.size());
            for (size_t i=1;i<aspt_name_vec.size();i++)
                aspt_tau_vec[i]=calc_tau(dist_vec[aspt_name_vec[0]][csv_path],dist_vec[aspt_name_vec[i]][csv_path],rel_eb,t2_vec);
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
        best_t2_vec[i][csv_path][rel_eb]=find_best_t2(dist_vec[aspt_name_vec[i]][csv_path],rel_eb,t2_vec);
        printf("csv_path=%s, rel_eb=%f, aspt=%s, best_t2=%f\n",csv_path.c_str(),rel_eb,aspt_name_vec[i].c_str(),best_t2_vec[i][csv_path][rel_eb]);
    }

    // 对每个eb，计算使用不同stencil pattern时的tau，使用最好的t2
    vector<unordered_map<double,unordered_map<tuple<string,string>,double>>> dist_2_vec(aspt_name_vec.size());
    for (auto &rel_eb:rel_eb_vec)
    for (auto &csv_path_base:csv_path_vec)
    for (auto &csv_path_oppo:csv_path_vec)
    for (size_t i=0;i<aspt_name_vec.size();i++)
        if (i==0)
        dist_2_vec[i][rel_eb][{csv_path_base,csv_path_oppo}]=get_dist_2(aspt_vec[i],standard_psnr,best_t2_vec[i],rel_eb,rel_eb_vec,csv_path_base,csv_path_oppo);
        else
        dist_2_vec[i][rel_eb][{csv_path_base,csv_path_oppo}]=get_dist_2(aspt_vec[i],aspt_psnr,best_t2_vec[i],rel_eb,rel_eb_vec,csv_path_base,csv_path_oppo);

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
}