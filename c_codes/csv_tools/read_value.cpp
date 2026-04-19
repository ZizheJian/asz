#pragma once

using namespace std;

template<typename T> string change_string_type(T value);
double read_value2(string &csv_path,string row_index,string column_name);

template<typename T1,typename T2>
double read_value(string &csv_path,T1 row_index,T2 column_name)
{
    return read_value2(csv_path,change_string_type(row_index),change_string_type(column_name));
}

template<typename T1,typename T2,typename T3>
double read_value(string &csv_path,T1 row_index1,T2 row_index2,T3 column_name)
{
    return read_value2(csv_path,change_string_type(row_index1)+","+change_string_type(row_index2),change_string_type(column_name));
}

double read_value2(string &csv_path,string row_index,string column_name)
{
    ifstream csv_file_in(csv_path);
    vector<string> lines;
    string line;
    while (getline(csv_file_in, line))
        lines.push_back(line);
    csv_file_in.close();
    bool found_row=false;
    for (uint64_t i=1;i<lines.size();i++)
        if (!lines[i].empty() && lines[i].size()>=row_index.size() && lines[i].substr(0,row_index.size())==row_index)
        {
            vector<string> headers;
            stringstream ss_header(lines[0]);
            string item;
            while (getline(ss_header,item,','))
                headers.push_back(item);
            vector<string> row_items;
            stringstream ss_row(lines[i]);
            while (getline(ss_row,item,','))
                row_items.push_back(item);
            bool found_column=false;
            for (uint64_t j=0;j<headers.size();j++)
                if (headers[j]==column_name)
                {
                    return stod(row_items[j]);
                    found_column=true;
                }
            if (!found_column)
                throw runtime_error("CSV file has no column "+column_name);
            break;
        }
    if (!found_row)
        throw runtime_error("CSV file has no row "+row_index);
}