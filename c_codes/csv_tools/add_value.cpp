#pragma once

using namespace std;

template<typename T> string change_string_type(T value);
void add_value2(string &csv_path,string row_name,string column_name,string value_str);

template<typename T1,typename T2,typename T3>
void add_value(string &csv_path,T1 row_name,T2 column_name,T3 value)
{
    add_value2(csv_path,change_string_type(row_name),change_string_type(column_name),change_string_type(value));
}

template<typename T1,typename T2,typename T3,typename T4>
void add_value(string &csv_path,T1 row_name1,T2 row_name2,T3 column_name,T4 value)
{
    add_value2(csv_path,change_string_type(row_name1)+","+change_string_type(row_name2),change_string_type(column_name),change_string_type(value));
}

void add_value2(string &csv_path,string row_name,string column_name,string value_str)
{
    ifstream csv_file_in(csv_path);
    vector<string> lines;
    string line;
    if (!csv_file_in.is_open())
        throw runtime_error("CSV file does not exist, cannot add item");
    while (getline(csv_file_in, line))
        lines.push_back(line);
    csv_file_in.close();
    vector<string> headers;
    stringstream ss(lines[0]);
    string item;
    while (getline(ss,item,','))
        headers.push_back(item);
    int column_index=-1;
    for (uint64_t i=0;i<headers.size();i++)
        if (headers[i]==column_name)
        {
            column_index=i;
            break;
        }
    if (column_index==-1)
        throw runtime_error("CSV file has no column "+column_name);
    int row_index=-1;
    for (uint64_t i=1;i<lines.size();i++)
        if (!lines[i].empty() && lines[i].size()>=row_name.size() && lines[i].substr(0,row_name.size())==row_name)
        {
            row_index=i;
            break;
        }
    if (row_index==-1)
        throw runtime_error("CSV file has no row "+row_name);
    vector<string> items;
    stringstream ss2(lines[row_index]);
    while (getline(ss2,item,','))
        items.push_back(item);
    for (uint64_t i=items.size();i<headers.size();i++)
        items.push_back("");
    items[column_index]=value_str;
    lines[row_index]="";
    for (size_t i=0;i<items.size();i++)
    {
        lines[row_index]+=items[i];
        if (i!=items.size()-1)
            lines[row_index]+=",";
    }
    ofstream csv_file_out(csv_path,ios::trunc);
    for (auto &l:lines)        
        csv_file_out<<l<<"\n";
    csv_file_out.close();
}