#pragma once

#include <vector>
#include <map>
#include <cmath>

using namespace std;

inline void hash_combine(int64_t &v1,int64_t v2)
{
    v1=v1*1145141919810+v2;
}

namespace std
{
    template<>
    struct hash<tuple<int64_t,int64_t>>
    {
        size_t operator()(const tuple<int64_t,int64_t> &t) const
        {
            auto[a,b]=t;
            int64_t h=0;
            hash_combine(h,a);
            hash_combine(h,b);
            return h;
        }
    };

    template<>
    struct hash<tuple<int64_t,int64_t,int64_t>>
    {
        size_t operator()(const tuple<int64_t,int64_t,int64_t> &t) const
        {
            auto[a,b,c]=t;
            int64_t h=0;
            hash_combine(h,a);
            hash_combine(h,b);
            hash_combine(h,c);
            return h;
        }
    };

    template<>
    struct hash<tuple<int64_t,int64_t,int64_t,int64_t>>
    {
        size_t operator()(const tuple<int64_t,int64_t,int64_t,int64_t> &t) const
        {
            auto[a,b,c,d]=t;
            int64_t h=0;
            hash_combine(h,a);
            hash_combine(h,b);
            hash_combine(h,c);
            hash_combine(h,d);
            return h;
        }
    };
}

double get_H1(vector<int64_t> &qb_vec,bool mmbc=false) //mmbc=Miller-Madow bias correction
{
    unordered_map<int64_t,uint64_t> qb_freq1;
    for (int64_t qb:qb_vec)
        qb_freq1[qb]++;
    double H1=0;
    for (auto &[qb,freq]:qb_freq1)
    {
        double p=(double)freq/qb_vec.size();
        H1-=p*log2(p);
    }
    if (mmbc)
        H1+=(qb_freq1.size()-1)/(2*qb_vec.size()*log(2));
    return H1;
}

double get_H2(vector<int64_t> &qb_vec,bool mmbc=false)
{
    unordered_map<int64_t,uint64_t> qb_freq1;
    unordered_map<tuple<int64_t,int64_t>,uint64_t> qb_freq2;
    for(size_t i=1;i<qb_vec.size();i++)
    {
        qb_freq1[qb_vec[i-1]]++;
        qb_freq2[{qb_vec[i-1],qb_vec[i]}]++;
    }
    double H2=0;
    for(auto &[p,freq]:qb_freq2)
    {
        double joint=(double)freq/(qb_vec.size()-1);
        double cond=(double)freq/qb_freq1[get<0>(p)];
        H2-=joint*log2(cond);
    }
    if (mmbc)
        H2+=(qb_freq2.size()-qb_freq1.size())/(2*(qb_vec.size()-1)*log(2));
    return H2;
}

double get_H3(vector<int64_t> &qb_vec,bool mmbc=false)
{
    unordered_map<tuple<int64_t,int64_t>,uint64_t> qb_freq2;
    unordered_map<tuple<int64_t,int64_t,int64_t>,uint64_t> qb_freq3;
    for(size_t i=2;i<qb_vec.size();i++)
    {
        qb_freq2[{qb_vec[i-2],qb_vec[i-1]}]++;
        qb_freq3[{qb_vec[i-2],qb_vec[i-1],qb_vec[i]}]++;
    }
    double H3=0;
    for(auto &[p,freq]:qb_freq3)
    {
        double joint=(double)freq/(qb_vec.size()-2);
        double cond=(double)freq/qb_freq2[{get<0>(p),get<1>(p)}];
        H3-=joint*log2(cond);
    }
    if (mmbc)
        H3+=(qb_freq3.size()-qb_freq2.size())/(2*(qb_vec.size()-2)*log(2));
    return H3;
}

double get_H4(vector<int64_t> &qb_vec,bool mmbc=false)
{
    unordered_map<tuple<int64_t,int64_t,int64_t>,uint64_t> qb_freq3;
    unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t> qb_freq4;
    for(size_t i=3;i<qb_vec.size();i++)
    {
        qb_freq3[{qb_vec[i-3],qb_vec[i-2],qb_vec[i-1]}]++;
        qb_freq4[{qb_vec[i-3],qb_vec[i-2],qb_vec[i-1],qb_vec[i]}]++;
    }
    double H4=0;
    for(auto &[p,freq]:qb_freq4)
    {
        double joint=(double)freq/(qb_vec.size()-3);
        double cond=(double)freq/qb_freq3[{get<0>(p),get<1>(p),get<2>(p)}];
        H4-=joint*log2(cond);
    }
    if (mmbc)
        H4+=(qb_freq4.size()-qb_freq3.size())/(2*(qb_vec.size()-3)*log(2));
    return H4;
}