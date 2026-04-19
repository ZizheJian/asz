#pragma once

using namespace std;

void read_all_values_in_column(string &csv_path,string column_name,vector<double> &values)
{
    ifstream csv_file_in(csv_path);
    vector<string> lines;
    string line;
    while (getline(csv_file_in, line))
        lines.push_back(line);
    csv_file_in.close();
    
    int64_t column_i=-1;
    vector<string> headers;
    stringstream ss_header(lines[0]);
    string item;
    while (getline(ss_header,item,','))
        headers.push_back(item);
    for (uint64_t i=0;i<headers.size();i++)
        if (headers[i]==column_name)
        {
            column_i=i;
            break;
        }
    if (column_i==-1)
        throw runtime_error("CSV file has no column "+column_name);

    set<double> value_set;
    for (uint64_t i=1;i<lines.size();i++)
        if (!lines[i].empty())
        {
            vector<string> items;
            stringstream ss_line(lines[i]);
            string item;
            while (getline(ss_line,item,','))
                items.push_back(item);
            if (items.size()>(uint64_t)column_i)
                value_set.insert(stod(items[column_i]));
        }
    values.insert(values.end(),value_set.begin(),value_set.end());
}