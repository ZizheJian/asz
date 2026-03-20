import numpy as np

with open("results_cubic_prediction.csv","r") as f:
    lines=f.readlines()
    arr=[line.strip().split(",") for line in lines]
    eb_set=set()
    val_name_set=set()
    for item in arr[0][1:]:
        item=item.strip().split("_")
        eb_set.add(item[0])
        val_name_set.add(item[1])
    eb_list=sorted(map(float,eb_set),reverse=True)
    val_name_list=sorted(list(val_name_set))
    ans=np.zeros((len(eb_list),len(val_name_list)))
    for line in arr[1:]:
        if line[0]=="0.3":
            for i in range(1,len(line)):
                eb=float(arr[0][i].strip().split("_")[0])
                val_name=arr[0][i].strip().split("_")[1]
                eb_index=eb_list.index(eb)
                val_name_index=val_name_list.index(val_name)
                ans[eb_index][val_name_index]=line[i]

with open("temp.csv","w") as f:
    f.write("eb,"+",".join(val_name_list)+"\n")
    for i,eb in enumerate(eb_list):
        f.write(str(eb)+","+",".join(map(str,ans[i]))+"\n")