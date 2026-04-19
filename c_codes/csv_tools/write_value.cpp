#pragma once

using namespace std;

template<typename T> string change_string_type(T value);
void write_value2(string &csv_path,string row_index,string column_name,string value_str);

template<typename T1,typename T2,typename T3>
void write_value(string &csv_path,T1 row_index,T2 column_name,T3 value)
{
    write_value2(csv_path,change_string_type(row_index),change_string_type(column_name),change_string_type(value));
}

template<typename T1,typename T2,typename T3,typename T4>
void write_value(string &csv_path,T1 row_index1,T2 row_index2,T3 column_name,T4 value)
{
    write_value2(csv_path,change_string_type(row_index1)+","+change_string_type(row_index2),change_string_type(column_name),change_string_type(value));
}

void write_value2(string &csv_path,string row_index,string column_name,string value_str)
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
            found_row=true;
            vector<string> headers;
            stringstream ss_header(lines[0]);
            string item;
            while (getline(ss_header,item,','))
                headers.push_back(item);
            vector<string> row_items;
            stringstream ss_row(lines[i]);
            while (getline(ss_row,item,','))
                row_items.push_back(item);
            while (row_items.size()<headers.size())
                row_items.push_back("");
            bool found_column=false;
            for (uint64_t j=0;j<headers.size();j++)
                if (headers[j]==column_name)
                {
                    row_items[j]=value_str;
                    found_column=true;
                }
            if (!found_column)
                throw runtime_error("CSV file has no column "+column_name);
            lines[i]="";
            for (uint64_t j=0;j<row_items.size();j++)     
            {
                lines[i]+=row_items[j];
                if (j!=row_items.size()-1)
                    lines[i]+=",";
            }
            break;
        }
    if (!found_row)
        throw runtime_error("CSV file has no row "+row_index);
    ofstream csv_file_out(csv_path,ios::trunc);
    for (auto &l:lines)      
    {
        csv_file_out.write(l.c_str(),l.size());
        csv_file_out.write("\n",1);
    }  
    csv_file_out.close();
}