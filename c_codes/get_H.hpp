#pragma once

#include <vector>
#include <map>
#include <cmath>

using namespace std;

struct Tuple2Hash{
    size_t operator()(const tuple<int64_t,int64_t>&t)const
    {
        auto[a,b]=t;
        size_t h=std::hash<int64_t>{}(a);
        h=h*1315423911u+std::hash<int64_t>{}(b);
        return h;
    }
};

struct Tuple3Hash{
    size_t operator()(const tuple<int64_t,int64_t,int64_t>&t)const
    {
        auto[a,b,c]=t;
        size_t h=std::hash<int64_t>{}(a);
        h=h*1315423911u+std::hash<int64_t>{}(b);
        h=h*1315423911u+std::hash<int64_t>{}(c);
        return h;
    }
};

struct Tuple4Hash{
    size_t operator()(const tuple<int64_t,int64_t,int64_t,int64_t>&t)const
    {
        auto[a,b,c,d]=t;
        size_t h=std::hash<int64_t>{}(a);
        h=h*1315423911u+std::hash<int64_t>{}(b);
        h=h*1315423911u+std::hash<int64_t>{}(c);
        h=h*1315423911u+std::hash<int64_t>{}(d);
        return h;
    }
};

double get_H1(vector<int64_t> &qb_vec)
{
    map<int64_t,uint64_t> qb_freq1;
    for (int64_t qb:qb_vec)
        qb_freq1[qb]++;
    double H1=0;
    for (auto &[qb,freq]:qb_freq1)
    {
        double prob=(double)freq/qb_vec.size();
        H1-=prob*log2(prob);
    }
    // H1+=(qb_freq1.size()-1)/(2*qb_vec.size()*log(2));
    return H1;
}

double get_H2(vector<int64_t> &qb_vec)
{
    unordered_map<int64_t,uint64_t> qb_freq1;
    unordered_map<pair<int64_t,int64_t>,uint64_t,Tuple2Hash> qb_freq2;
    for(size_t i=1;i<qb_vec.size();i++)
    {
        qb_freq1[qb_vec[i-1]]++;
        qb_freq2[{qb_vec[i-1],qb_vec[i]}]++;
    }
    double H2=0;
    for(auto &[p,freq]:qb_freq2)
    {
        double joint=(double)freq/(qb_vec.size()-1);
        double cond=(double)freq/qb_freq1[p.first];
        H2-=joint*log2(cond);
    }
    // H2+=(qb_freq2.size()-qb_freq1.size())/(2*(qb_vec.size()-1)*log(2));
    return H2;
}

double get_H3(vector<int64_t> &qb_vec)
{
    unordered_map<pair<int64_t,int64_t>,uint64_t,Tuple2Hash> qb_freq2;
    unordered_map<tuple<int64_t,int64_t,int64_t>,uint64_t,Tuple3Hash> qb_freq3;
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
    // H3+=(qb_freq3.size()-qb_freq2.size())/(2*(qb_vec.size()-2)*log(2));
    return H3;
}

double get_H4(vector<int64_t> &qb_vec)
{
    unordered_map<tuple<int64_t,int64_t,int64_t>,uint64_t,Tuple3Hash> qb_freq3;
    unordered_map<tuple<int64_t,int64_t,int64_t,int64_t>,uint64_t,Tuple4Hash> qb_freq4;
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
    // H4+=(qb_freq4.size()-qb_freq3.size())/(2*(qb_vec.size()-3)*log(2));
    return H4;
}