#pragma once

using namespace std;

template<typename T> string change_string_type(T value);
void add_column2(string &csv_path,string column_name);

template<typename T>
void add_column(string &csv_path,T column_name)
{
    add_column2(csv_path,change_string_type(column_name));
}

template<typename T1,typename T2>
void add_column(string &csv_path,T1 column_name1,T2 column_name2)
{
    add_column2(csv_path,change_string_type(column_name1));
    add_column2(csv_path,change_string_type(column_name2));
}

void add_column2(string &csv_path,string column_name)
{
    ifstream csv_file_in(csv_path);
    vector<string> lines;
    string line;
    if (csv_file_in.is_open())
    {
        while (getline(csv_file_in, line))
            lines.push_back(line);
        csv_file_in.close();
    }
    bool modified=false;
    if (lines.empty())
    {
        lines.push_back(column_name);
        modified=true;
    }
    else if (lines[0].empty())
    {
        lines[0]=column_name;
        modified=true;
    }
    else
    {
        vector<string> headers;
        stringstream ss(lines[0]);
        string item;
        while (getline(ss,item,','))
            headers.push_back(item);
        bool has_column_name=false;
        for (auto &h:headers)
            if (h==column_name)
            {
                has_column_name=true;
                break;
            }
        if (!has_column_name)
        {
            lines[0]+=","+column_name;
            for (size_t i=1;i<lines.size();i++)
                lines[i]+=",";
            modified=true;
        }
    }
    if (modified)
    {
        ofstream csv_file_out(csv_path,ios::trunc);
        for (auto &l:lines)
            csv_file_out<<l<<"\n";
        csv_file_out.close();
    }
}