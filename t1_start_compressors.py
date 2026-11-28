import argparse,array,csv,hashlib,json,math,os,re
from pathlib import Path

import numpy as np

from third_party.csv_tools.py_codes.write_csv_item import write_csv_item
from third_party.experiment_launcher.py_codes.experiment_launcher import cmake_build,cmake_build_and_install,cmake_install,job_command_from_argv,load_experiment_config,resolve_config_path,resolve_install_dir,resolve_project_path,submit_slurm_job
from third_party.get_max_cpus.py_codes.get_max_cpus import get_max_cpus
from third_party.run_command.run_command import run_command

project_root=Path(__file__).resolve().parent
config_directory=project_root/"configs"
slurm_account="cis240669" # config的slurm里没有写account时用这个账户
slurm_log_path=project_root/"results/slurm/%x-%j.out" # 作业日志，%x是作业名（config名），%j是作业号
supported_compressors=("asz","sz3","qoz","zfp","sperr")
traversal_orders={(1,2,0):"120",(0,2,1):"021",(0,1,2):"012"}
asz_parameter_keys=("pivot_eb_ratio","eb_ratio","slope_ratio","block_pivot_ratio","max_layer_num","full_predictor_search_layer_num","t_precision")
asz_compress_parameter_keys=("generate_config_sample_stride","h1_block_sampling_num","stat_eb_ratio","predictor_family_suffix_layers","predictor_family_sample_blocks","predictor_family_sample_point_limit","predictor_family_sample_fraction_limit","predictor_family_coarse_probe_block_pivot_ratio","predictor_family_fine_probe_block_pivot_ratio","predictor_family_fine_eb_threshold","default_slope_invalid_ratio_threshold","default_slope_fallback","default_slope_eb_span","t_min","t_max")
asz_block_policy_keys=("coarse_block_pivot_ratio","fine_block_pivot_ratio")


def resolve_task_path(path):
    return Path(resolve_project_path(path,project_root)).resolve()

def prepare_methods(method_list,task_id):
    if not isinstance(method_list,list) or not method_list:
        raise ValueError(f"task {task_id}的method_list必须是非空列表")
    methods=[]
    for method_id,method in enumerate(method_list):
        if isinstance(method,str):
            prepared={"name":method,"compressor":method}
        elif isinstance(method,dict):
            allowed_keys={"name","compressor","read_plan","write_plan","predictor_family","report_t_histogram",*asz_parameter_keys,*asz_compress_parameter_keys,*asz_block_policy_keys}
            unknown=method.keys()-allowed_keys
            if unknown:
                raise ValueError(f"task {task_id}的method {method_id}包含未知参数：{','.join(sorted(unknown))}")
            if not isinstance(method.get("name"),str) or not method["name"]:
                raise ValueError(f"task {task_id}的method {method_id}缺少有效name")
            if not isinstance(method.get("compressor"),str):
                raise ValueError(f"task {task_id}的method {method_id}缺少有效compressor")
            prepared=dict(method)
        else:
            raise TypeError(f"task {task_id}的method {method_id}必须是字符串或object")
        if prepared["compressor"] not in supported_compressors:
            raise ValueError(f"task {task_id}的method {method_id}使用未知compressor：{prepared['compressor']}")
        for key in ("read_plan","write_plan"):
            if key in prepared and (prepared["compressor"]!="asz" or not isinstance(prepared[key],str) or not prepared[key]):
                raise ValueError(f"task {task_id}的method {method_id}的{key}只能用于asz且必须是非空字符串")
        if "read_plan" in prepared and "write_plan" in prepared:
            raise ValueError(f"task {task_id}的method {method_id}不能同时read_plan和write_plan")
        if "predictor_family" in prepared:
            if prepared["compressor"]!="asz" or prepared["predictor_family"] not in ("cubic","quintic"):
                raise ValueError(f"task {task_id}的method {method_id}的predictor_family只能是cubic或quintic且只能用于asz")
        if "report_t_histogram" in prepared and (prepared["compressor"]!="asz" or not isinstance(prepared["report_t_histogram"],bool)):
            raise ValueError(f"task {task_id}的method {method_id}的report_t_histogram只能是ASZ布尔参数")
        for key in (*asz_parameter_keys,*asz_compress_parameter_keys):
            if key not in prepared:
                continue
            value=prepared[key]
            if prepared["compressor"]!="asz":
                raise ValueError(f"task {task_id}的method {method_id}只有asz可以设置{key}")
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError(f"task {task_id}的method {method_id}的{key}必须是有限数字")
            if key in ("block_pivot_ratio","max_layer_num","full_predictor_search_layer_num","generate_config_sample_stride","h1_block_sampling_num","predictor_family_suffix_layers","predictor_family_sample_blocks","predictor_family_sample_point_limit","predictor_family_coarse_probe_block_pivot_ratio","predictor_family_fine_probe_block_pivot_ratio","t_precision"):
                if not isinstance(value,int) or value<=0:
                    raise ValueError(f"task {task_id}的method {method_id}的{key}必须是正整数")
                if key in ("max_layer_num","full_predictor_search_layer_num") and value>63:
                    raise ValueError(f"task {task_id}的method {method_id}的{key}不能超过63")
                if key=="t_precision" and (value<16 or value%16):
                    raise ValueError(f"task {task_id}的method {method_id}的t_precision必须是16的正整数倍")
            elif key in ("t_min","t_max"):
                if not 0<=value<=0.5:
                    raise ValueError(f"task {task_id}的method {method_id}的{key}必须在[0,0.5]内")
            elif key=="default_slope_fallback":
                if value<=0:
                    raise ValueError(f"task {task_id}的method {method_id}的default_slope_fallback必须为正数")
            elif key=="default_slope_eb_span":
                if value<=1:
                    raise ValueError(f"task {task_id}的method {method_id}的default_slope_eb_span必须大于1")
            elif not 0<value<=1:
                raise ValueError(f"task {task_id}的method {method_id}的{key}必须在(0,1]内")
        if ("t_min" in prepared)!=("t_max" in prepared):
            raise ValueError(f"task {task_id}的method {method_id}必须同时设置t_min和t_max")
        if "t_min" in prepared and (prepared["t_min"]>0.25 or prepared["t_max"]<0.3125 or prepared["t_min"]>prepared["t_max"]):
            raise ValueError(f"task {task_id}的method {method_id}的t范围必须包含4/16和5/16")
        if "t_min" in prepared:
            t_precision=prepared.get("t_precision",32)
            if any(not math.isclose(prepared[key]*t_precision,round(prepared[key]*t_precision),abs_tol=1e-9) for key in ("t_min","t_max")):
                raise ValueError(f"task {task_id}的method {method_id}的t_min和t_max必须能t_precision精确表示")
        if prepared.get("t_precision",32)%32 or prepared.get("t_min",1/16)>1/16 or prepared.get("t_max",6/16)<11/32:
            raise ValueError(f"task {task_id}的method {method_id}的block系数候选需要t_precision是32的倍数且t范围覆盖[1/16,11/32]")
        policy_key_count=sum(key in prepared for key in asz_block_policy_keys)
        if policy_key_count==1:
            raise ValueError(f"task {task_id}的method {method_id}必须同时设置coarse_block_pivot_ratio和fine_block_pivot_ratio")
        if policy_key_count:
            if prepared["compressor"]!="asz" or "block_pivot_ratio" in prepared:
                raise ValueError(f"task {task_id}的method {method_id}的粗细block ratio策略只能用于asz且不能同时设置block_pivot_ratio")
            for key in asz_block_policy_keys:
                if isinstance(prepared[key],bool) or not isinstance(prepared[key],int) or prepared[key]<=0:
                    raise ValueError(f"task {task_id}的method {method_id}的{key}必须是正整数")
        methods.append(prepared)
    names=[method["name"] for method in methods]
    if len(names)!=len(set(names)):
        raise ValueError(f"task {task_id}的method name不能重复")
    return methods

required_task_keys=("data_path_list","data_shape","rel_eb_list","method_list")
optional_task_keys=("cleanup_after_each_test","comparison_baseline","summary_csv","output_directory")
path_task_keys=("data_path_list","summary_csv","output_directory")

# 读取config，检查参数，相对路径接在项目根目录后面。返回的slurm是作业资源，config里没写时为None
def load_config(config_path):
    config=load_experiment_config(config_path,required_keys=required_task_keys,optional_keys=optional_task_keys,path_keys=path_task_keys,project_root=project_root)
    prepared=[]
    for task_id,task in enumerate(config.tasks):
        data_path_list=task["data_path_list"]
        if not isinstance(data_path_list,list) or not data_path_list:
            raise ValueError(f"task {task_id}的data_path_list必须是非空字符串列表")
        if len(data_path_list)!=len(set(data_path_list)):
            raise ValueError(f"task {task_id}的data_path_list不能包含重复项")
        shape=task["data_shape"]
        if not isinstance(shape,list) or len(shape)!=3 or any(isinstance(value,bool) or not isinstance(value,int) or value<7 for value in shape):
            raise ValueError(f"task {task_id}的data_shape必须包含三个不小于7的整数")
        rel_eb_list=task["rel_eb_list"]
        if not isinstance(rel_eb_list,list) or not rel_eb_list or any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0 for value in rel_eb_list):
            raise ValueError(f"task {task_id}的rel_eb_list必须是非空有限正数列表")
        if len(rel_eb_list)!=len(set(rel_eb_list)):
            raise ValueError(f"task {task_id}的rel_eb_list不能包含重复项")
        methods=prepare_methods(task["method_list"],task_id)
        if "cleanup_after_each_test" in task and not isinstance(task["cleanup_after_each_test"],bool):
            raise ValueError(f"task {task_id}的cleanup_after_each_test必须是布尔值")
        method_names={method["name"] for method in methods}
        comparison_baseline=task.get("comparison_baseline")
        if comparison_baseline is not None and comparison_baseline not in method_names:
            raise ValueError(f"task {task_id}的comparison_baseline不在method_list中")
        if (comparison_baseline is None)!=(task.get("summary_csv") is None):
            raise ValueError(f"task {task_id}必须同时提供comparison_baseline和summary_csv")
        for key in ("summary_csv","output_directory"):
            if task.get(key) is not None and not isinstance(task[key],str):
                raise ValueError(f"task {task_id}的{key}必须是字符串")
        if len(data_path_list)>1:
            for method in methods:
                if "write_plan" in method and "{stem}" not in method["write_plan"] and "{name}" not in method["write_plan"]:
                    raise ValueError(f"task {task_id}有多个数据文件，method {method['name']}的write_plan必须包含{{stem}}或{{name}}")
        # 数据路径只规范化、不解析符号链接，它会写进汇总CSV的DATA_PATH列
        prepared_task={**task,"data_path_list":[Path(os.path.abspath(path)) for path in data_path_list],"rel_eb_list":[float(value) for value in rel_eb_list],"method_list":methods}
        for key in ("summary_csv","output_directory"):
            if prepared_task.get(key) is not None:
                prepared_task[key]=Path(prepared_task[key]).resolve()
        prepared.append(prepared_task)
    config.tasks=prepared
    return config

def validate_data_file(path,shape):
    if not path.is_file():
        raise FileNotFoundError(f"找不到数据文件：{path}")
    expected_bytes=math.prod(shape)*4
    actual_bytes=path.stat().st_size
    if actual_bytes!=expected_bytes:
        raise ValueError(f"数据文件大小错误：{path}有{actual_bytes}字节，data_shape对应{expected_bytes}字节")

def load_plan(path):
    with open(path,encoding="utf-8") as plan_file:
        document=json.load(plan_file)
    if not isinstance(document,dict) or document.get("version") not in (1,2) or not isinstance(document.get("plans"),list):
        raise ValueError(f"plan格式错误：{path}")
    plans=[]
    for plan_id,plan in enumerate(document["plans"]):
        if not isinstance(plan,dict) or not isinstance(plan.get("rel_eb"),(int,float)) or not isinstance(plan.get("layers"),list) or not plan["layers"]:
            raise ValueError(f"plan {plan_id}格式错误：{path}")
        predictors=[]
        for layer_id,layer in enumerate(plan["layers"]):
            if not isinstance(layer,dict) or set(layer)!={"prediction_direction","traversal_order"}:
                raise ValueError(f"plan {plan_id}的layer {layer_id}格式错误：{path}")
            direction=layer["prediction_direction"]
            traversal=layer["traversal_order"]
            if not isinstance(direction,int) or direction not in (0,1,2):
                raise ValueError(f"plan {plan_id}的layer {layer_id}预测方向错误：{path}")
            if not isinstance(traversal,list) or tuple(traversal) not in traversal_orders:
                raise ValueError(f"plan {plan_id}的layer {layer_id}遍历顺序错误：{path}")
            predictors.append(f"cubic{direction}_{traversal_orders[tuple(traversal)]}")
        predictor_family=plan.get("predictor_family","cubic")
        if predictor_family not in ("cubic","quintic"):
            raise ValueError(f"plan {plan_id}的predictor_family错误：{path}")
        plans.append((float(plan["rel_eb"]),predictors,predictor_family))
    return plans

def predictors_for_rel_eb(plans,rel_eb,path):
    matches=[(predictors,predictor_family) for plan_rel_eb,predictors,predictor_family in plans if math.isclose(plan_rel_eb,rel_eb,rel_tol=1e-12,abs_tol=0.0)]
    if len(matches)!=1:
        raise ValueError(f"{path}中应当恰好有一个rel_eb={rel_eb:g}的plan，实际找到{len(matches)}个")
    return matches[0]

def parse_predictors(output):
    matches=re.findall(r'^predictor_vec=\{(.*)\};\r?$',output,re.MULTILINE)
    if len(matches)!=1:
        raise RuntimeError(f"未能唯一解析ASZ predictor_vec，实际找到{len(matches)}个")
    predictors=re.findall(r'"([^"]+)"',matches[0])
    if not predictors:
        raise RuntimeError("ASZ predictor_vec为空")
    return predictors

def parse_predictor_family(output):
    matches=re.findall(r'^predictor_family=(cubic|quintic);\r?$',output,re.MULTILINE)
    if len(matches)!=1:
        raise RuntimeError(f"未能唯一解析ASZ predictor_family，实际找到{len(matches)}个")
    return matches[0]

def parse_predictor_family_selection(output):
    time_matches=re.findall(r"^Predictor family selection time: ([0-9.eE+-]+) s\r?$",output,re.MULTILINE)
    if len(time_matches)!=1:
        raise RuntimeError(f"未能唯一解析ASZ predictor family selection time，实际找到{len(time_matches)}个")
    result={"predictor_family_selection_time":float(time_matches[0])}
    h1_matches=re.findall(r"^Predictor family selection: selector=h1, .*$",output,re.MULTILINE)
    if len(h1_matches)==1:
        values=dict(item.split("=",1) for item in h1_matches[0].strip().split(": ",1)[1].split(", "))
        result.update({"predictor_family_selector":"h1","predictor_family_suffix_layers":int(values["suffix_layers"]),"predictor_family_blocks":int(values["blocks"]),"predictor_family_sampled_block_points":int(values["sampled_block_points"]),"predictor_family_sample_point_budget":int(values["sample_point_budget"]),"predictor_family_probe_block_pivot_ratio":int(values["probe_block_pivot_ratio"]),"predictor_family":values["family"],"predictor_family_fallback":"fallback" in values})
        if "points" in values:
            result.update({"predictor_family_samples":int(values["points"]),"cubic_mse":float(values["cubic_mse"]),"quintic_mse":float(values["quintic_mse"]),"cubic_psnr":float(values["cubic_psnr"]),"quintic_psnr":float(values["quintic_psnr"]),"cubic_h1":float(values["cubic_h1"]),"quintic_h1":float(values["quintic_h1"]),"six_score_gain":float(values["six_score_gain"])})
        return result
    raise RuntimeError("未能唯一解析ASZ predictor family selection")

def parse_default_slope_statistics(output):
    matches=re.findall(r"^Default slope statistics: max_invalid_ratio=([0-9.eE+-]+), fallback=(true|false), reason=([a-z_]+), slope=([0-9.eE+-]+)\r?$",output,re.MULTILINE)
    if len(matches)!=1:
        raise RuntimeError(f"未能唯一解析ASZ default slope statistics，实际找到{len(matches)}个")
    invalid_ratio,fallback,reason,slope=matches[0]
    return {"default_slope_max_invalid_ratio":float(invalid_ratio),"default_slope_fallback_used":fallback=="true","default_slope_fallback_reason":reason,"default_slope":float(slope)}

def plan_document(plan_entries):
    plans=[]
    for rel_eb,(predictors,predictor_family) in sorted(plan_entries.items(),reverse=True):
        layers=[]
        for predictor in predictors:
            match=re.fullmatch(r"cubic([012])_(120|021|012)",predictor)
            if match is None:
                raise ValueError(f"无法写入未知predictor：{predictor}")
            layers.append({"prediction_direction":int(match.group(1)),"traversal_order":[int(value) for value in match.group(2)]})
        plans.append({"rel_eb":rel_eb,"predictor_family":predictor_family,"layers":layers})
    return {"version":2,"plans":plans}

def write_plan(path,plan_entries):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=path.with_name(path.name+".tmp")
    with open(temporary_path,"w",encoding="utf-8") as plan_file:
        json.dump(plan_document(plan_entries),plan_file,indent=2)
        plan_file.write("\n")
    os.replace(temporary_path,path)
    print(f"写入plan：{path}",flush=True)

def resolve_plan_path(path_template,data_path):
    try:
        path=path_template.format(stem=data_path.stem,name=data_path.name)
    except KeyError as error:
        raise ValueError(f"plan路径使用未知模板参数：{error.args[0]}") from error
    return resolve_task_path(path)

# 用CMake配置、编译并安装一个baseline或依赖库，路径都相对于项目根目录。
# with_zstd为True时，cmake运行时PKG_CONFIG_PATH指向项目里编译的zstd，SZ3和QoZ通过pkg-config找到它
def build_dependency(source_path,build_path,install_path,options,build_max_cpus,silent,with_zstd=False):
    environment=["cmake","-E","env",f"PKG_CONFIG_PATH={project_root/'install/common_zstd_install/lib/pkgconfig'}"] if with_zstd else []
    cmake_build_and_install(lambda command:run_command([*environment,*command],silent),*(project_root/path for path in (source_path,build_path,install_path)),options,build_max_cpus)

# 编译这一步：编译并安装用到的baseline（和SZ3、QoZ需要的zstd一起装在install/*_install下，运行时直接用那里的程序），再把ASZ编译到build，ASZ本身不安装。
# build里配置的默认安装目录是install，所以直接运行cmake --install build时装到install
def build_project(baselines,build_max_cpus,silent):
    zstd_library=f"-Dpkgcfg_lib_ZSTD_zstd:FILEPATH={project_root/'install/common_zstd_install/lib/libzstd.a'}"
    if any(baseline in ("sz3","qoz") for baseline in baselines):
        build_dependency("third_party/zstd/build/cmake","build/common_zstd_build","install/common_zstd_install",["-DCMAKE_BUILD_TYPE=Release","-DCMAKE_INSTALL_LIBDIR=lib","-DZSTD_BUILD_SHARED=OFF","-DZSTD_BUILD_STATIC=ON","-DZSTD_BUILD_PROGRAMS=OFF","-DZSTD_BUILD_TESTS=OFF"],build_max_cpus,silent)
    for baseline in baselines:
        if baseline=="sz3":
            build_dependency("third_party/SZ3","build/sz3_build","install/sz3_install",["-UZSTD_*",zstd_library,"-DBUILD_SHARED_LIBS=OFF","-DSZ3_USE_BUNDLED_ZSTD=OFF"],build_max_cpus,silent,with_zstd=True)
        elif baseline=="qoz":
            build_dependency("third_party/QoZ","build/qoz_build","install/qoz_install",["-UZSTD_*",zstd_library,"-DBUILD_SHARED_LIBS=OFF","-DQoZ_USE_BUNDLED_ZSTD=OFF","-DQoZ_DEBUG_TIMINGS=OFF"],build_max_cpus,silent,with_zstd=True)
        elif baseline in ("zfp","sperr"):
            build_dependency(f"third_party/{baseline}",f"build/{baseline}_build",f"install/{baseline}_install",["-DBUILD_SHARED_LIBS=OFF"],build_max_cpus,silent)
    cmake_build(lambda command:run_command(command,silent),project_root/"c_codes",project_root/"build",project_root/"install",["-DCODE_NAME=s1_compress"],build_max_cpus)

# 安装这一步：把build里的ASZ装到install_dir，不管build里的程序是不是最新的
def install_project(install_dir,silent):
    cmake_install(lambda command:run_command(command,silent),project_root/"build",install_dir)

def parse_asz_result(output):
    patterns={"cr":r"^CR= ([0-9.eE+-]+)\r?$","data_range_time":r"^Data range time: ([0-9.eE+-]+)","compression_time":r"^Compression time: ([0-9.eE+-]+)","decompression_time":r"^Decompression time: ([0-9.eE+-]+)"}
    result={}
    for key,pattern in patterns.items():
        matches=re.findall(pattern,output,re.MULTILINE)
        if not matches:
            raise RuntimeError(f"未能解析ASZ的{key}")
        result[key]=float(matches[-1])
    matches=re.findall(r"^Generate config time: ([0-9.eE+-]+)",output,re.MULTILINE)
    if matches:
        result["generate_config_time"]=float(matches[-1])
    matches=re.findall(r"^Get default slope time: ([0-9.eE+-]+)",output,re.MULTILINE)
    if matches:
        result["get_default_slope_time"]=float(matches[-1])
    matches=re.findall(r"^T histogram:([0-9=,]+)\r?$",output,re.MULTILINE)
    if matches:
        histogram={key:int(value) for key,value in (item.split("=") for item in matches[-1].split(","))}
        result["t_histogram"]=json.dumps(histogram,separators=(",",":"))
        fallback_matches=re.findall(r"^T fallback count:([0-9]+)\r?$",output,re.MULTILINE)
        if not fallback_matches:
            raise RuntimeError("未能解析ASZ的t fallback数量")
        result["t_fallback_count"]=int(fallback_matches[-1])
    return result

def parse_sz_result(output,compressor):
    patterns={"cr":r"^compression ratio = ([0-9.eE+-]+)","psnr":r"^PSNR = ([0-9.eE+-]+)","compression_time":r"^compression time = ([0-9.eE+-]+)","decompression_time":r"^decompression time = ([0-9.eE+-]+)"}
    result={}
    for key,pattern in patterns.items():
        matches=re.findall(pattern,output,re.MULTILINE)
        if not matches:
            raise RuntimeError(f"未能解析{compressor}的{key}")
        result[key]=float(matches[-1])
    result["br"]=32/result["cr"]
    return result

def parse_codec_time(output,compressor,operation):
    matches=re.findall(rf"^{operation} time = ([0-9.eE+-]+)",output,re.MULTILINE)
    if not matches:
        raise RuntimeError(f"未能解析{compressor}的{operation} time")
    return float(matches[-1])

def calculate_float32_metrics(original_path,reconstructed_path):
    original_size=original_path.stat().st_size
    reconstructed_size=reconstructed_path.stat().st_size
    if reconstructed_size!=original_size:
        raise RuntimeError(f"重建文件大小错误：{reconstructed_path}有{reconstructed_size}字节，原文件有{original_size}字节")
    minimum=math.inf
    maximum=-math.inf
    squared_error_sum=0.0
    max_error=0.0
    element_count=0
    with open(original_path,"rb") as original_file,open(reconstructed_path,"rb") as reconstructed_file:
        while True:
            original=np.fromfile(original_file,dtype=np.float32,count=1<<20)
            if original.size==0:
                break
            reconstructed=np.fromfile(reconstructed_file,dtype=np.float32,count=original.size)
            if reconstructed.size!=original.size:
                raise RuntimeError(f"重建文件提前结束：{reconstructed_path}")
            if not np.all(np.isfinite(original)) or not np.all(np.isfinite(reconstructed)):
                raise RuntimeError(f"原始文件或重建文件包含非有限值：{original_path}")
            difference=original.astype(np.float64)-reconstructed
            minimum=min(minimum,float(np.min(original)))
            maximum=max(maximum,float(np.max(original)))
            squared_error_sum+=float(np.dot(difference,difference))
            max_error=max(max_error,float(np.max(np.abs(difference))))
            element_count+=original.size
        if reconstructed_file.read(1):
            raise RuntimeError(f"重建文件包含多余数据：{reconstructed_path}")
    value_range=maximum-minimum
    if element_count==0 or not math.isfinite(value_range) or value_range<=0:
        raise RuntimeError(f"数据范围无效：{original_path}")
    mse=squared_error_sum/element_count
    psnr=math.inf if mse==0 else 20*math.log10(value_range)-10*math.log10(mse)
    return {"psnr":psnr,"max_error":max_error,"value_range":value_range}

def error_bound_tolerance(absolute_eb):
    return absolute_eb*.01

def calculate_float32_range(path):
    minimum=math.inf
    maximum=-math.inf
    with open(path,"rb") as data_file:
        while chunk:=data_file.read(4*(1<<20)):
            values=array.array("f")
            values.frombytes(chunk)
            minimum=min(minimum,min(values))
            maximum=max(maximum,max(values))
    if not math.isfinite(minimum) or not math.isfinite(maximum) or minimum==maximum:
        raise ValueError(f"数据范围无效：{path}")
    return maximum-minimum

def codec_output_path(task,suffix):
    data_path=task["data_path"]
    output_directory=task.get("output_directory")
    if output_directory is None:
        return Path(str(data_path)+suffix)
    prefix=hashlib.sha256(str(data_path).encode("utf-8")).hexdigest()[:12]
    return output_directory/f"{prefix}_{data_path.name}{suffix}"

def run_asz(task,rel_eb,predictors,method,asz_bin_directory,plan_predictor_family=None):
    shape=task["data_shape"]
    data_path=task["data_path"]
    compressed_path=codec_output_path(task,".asz")
    reconstructed_path=codec_output_path(task,".bin")
    common=["-f","-i",data_path,"-3",*shape,"-M","REL",f"{rel_eb:.17g}"]
    option_names={"pivot_eb_ratio":"--pivot-eb-ratio","eb_ratio":"--eb-ratio","slope_ratio":"--slope-ratio","block_pivot_ratio":"--block-pivot-ratio","max_layer_num":"--max-layer-num","full_predictor_search_layer_num":"--full-predictor-search-layer-num","generate_config_sample_stride":"--generate-config-sample-stride","h1_block_sampling_num":"--h1-block-sampling-num","stat_eb_ratio":"--stat-eb-ratio","predictor_family_suffix_layers":"--predictor-family-suffix-layers","predictor_family_sample_blocks":"--predictor-family-sample-blocks","predictor_family_sample_point_limit":"--predictor-family-sample-point-limit","predictor_family_sample_fraction_limit":"--predictor-family-sample-fraction-limit","predictor_family_coarse_probe_block_pivot_ratio":"--predictor-family-coarse-probe-block-pivot-ratio","predictor_family_fine_probe_block_pivot_ratio":"--predictor-family-fine-probe-block-pivot-ratio","predictor_family_fine_eb_threshold":"--predictor-family-fine-eb-threshold","default_slope_invalid_ratio_threshold":"--default-slope-invalid-ratio-threshold","default_slope_fallback":"--default-slope-fallback","default_slope_eb_span":"--default-slope-eb-span","t_precision":"--t-precision","t_min":"--t-min","t_max":"--t-max"}
    method_options=dict(method)
    if plan_predictor_family is not None:
        method_options.setdefault("predictor_family",plan_predictor_family)
    if all(key in method_options for key in asz_block_policy_keys):
        method_options["block_pivot_ratio"]=method_options["fine_block_pivot_ratio"] if rel_eb<=1e-4 else method_options["coarse_block_pivot_ratio"]
    else:
        method_options.setdefault("block_pivot_ratio",96 if rel_eb<=1e-4 else 3)
    for key in asz_parameter_keys:
        if key in method_options:
            common.extend([option_names[key],method_options[key]])
    if "predictor_family" in method_options:
        common.extend(["--predictor-family",method_options["predictor_family"]])
    compress_command=[asz_bin_directory/"s1_compress",*common,"-z",compressed_path,"-o",reconstructed_path]
    for key in asz_compress_parameter_keys:
        if key in method_options:
            compress_command.extend([option_names[key],method_options[key]])
    if method_options.get("report_t_histogram",False):
        compress_command.append("--report-t-histogram")
    if predictors is not None:
        compress_command.extend(["--predictor-plan",",".join(predictors)])
    compression_output=run_command(compress_command)
    decompression_output=run_command([asz_bin_directory/"s1_decompress",*common,"-z",compressed_path,"-o",reconstructed_path])
    output=compression_output+decompression_output
    reported=parse_asz_result(output)
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,reconstructed_path)
    absolute_eb=rel_eb*metrics["value_range"]
    tolerance=error_bound_tolerance(absolute_eb)
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"asz违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    if not math.isclose(reported["cr"],cr,rel_tol=1e-5,abs_tol=1e-6):
        raise RuntimeError(f"asz报告的CR与压缩文件不一致：reported={reported['cr']},actual={cr}")
    result={"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size,"data_range_time":reported["data_range_time"],"compression_time":reported["compression_time"],"decompression_time":reported["decompression_time"]}
    if "generate_config_time" in reported:
        result["generate_config_time"]=reported["generate_config_time"]
    if "get_default_slope_time" in reported:
        result["get_default_slope_time"]=reported["get_default_slope_time"]
    if "t_histogram" in reported:
        result["t_histogram"]=reported["t_histogram"]
        result["t_fallback_count"]=reported["t_fallback_count"]
    actual_predictor_family=parse_predictor_family(compression_output)
    result.update(parse_default_slope_statistics(compression_output))
    if method_options.get("predictor_family") is None:
        result.update(parse_predictor_family_selection(compression_output))
        if result["predictor_family"]!=actual_predictor_family:
            raise RuntimeError("ASZ predictor family selection与最终配置不一致")
    else:
        result["predictor_family"]=actual_predictor_family
    preprocessing_keys=("get_default_slope_time","generate_config_time","predictor_family_selection_time")
    result["preprocessing_time"]=sum(result.get(key,0.0) for key in preprocessing_keys)
    return result,parse_predictors(compression_output),actual_predictor_family

def run_sz_variant(compressor,task,rel_eb):
    data_path=task["data_path"]
    shape=task["data_shape"]
    compressed_path=codec_output_path(task,f".{compressor}")
    reconstructed_path=codec_output_path(task,f".{compressor}.bin")
    executable=project_root/f"install/{compressor}_install/bin"/("sz3" if compressor=="sz3" else "qoz")
    command=[executable,"-f","-i",data_path,"-z",compressed_path,"-o",reconstructed_path,"-3",shape[2],shape[1],shape[0],"-M","REL",f"{rel_eb:.17g}","-a"]
    if compressor=="qoz":
        command.extend(["-q","4"])
    output=run_command(command,silent=True)
    reported=parse_sz_result(output,compressor)
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,reconstructed_path)
    absolute_eb=rel_eb*metrics["value_range"]
    tolerance=error_bound_tolerance(absolute_eb)
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"{compressor}违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    if not math.isclose(reported["cr"],cr,rel_tol=1e-5,abs_tol=1e-6):
        raise RuntimeError(f"{compressor}报告的CR与压缩文件不一致：reported={reported['cr']},actual={cr}")
    if not math.isclose(reported["psnr"],metrics["psnr"],rel_tol=1e-7,abs_tol=1e-5):
        raise RuntimeError(f"{compressor}报告的PSNR与独立计算不一致：reported={reported['psnr']},actual={metrics['psnr']}")
    return {"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size,"compression_time":reported["compression_time"],"decompression_time":reported["decompression_time"]}

def run_zfp(task,rel_eb,value_range):
    data_path=task["data_path"]
    shape=task["data_shape"]
    compressed_path=codec_output_path(task,".zfp")
    decompressed_path=codec_output_path(task,".zfp.bin")
    absolute_eb=rel_eb*value_range
    executable=project_root/"install/zfp_install/bin/zfp"
    dimensions=["-3",shape[2],shape[1],shape[0]]
    absolute_eb_text=f"{absolute_eb:.17g}"
    compression_output=run_command([executable,"-f","-i",data_path,"-z",compressed_path,*dimensions,"-a",absolute_eb_text],silent=True)
    decompression_output=run_command([executable,"-f","-z",compressed_path,"-o",decompressed_path,*dimensions,"-a",absolute_eb_text],silent=True)
    compression_time=parse_codec_time(compression_output,"zfp","compression")
    decompression_time=parse_codec_time(decompression_output,"zfp","decompression")
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,decompressed_path)
    tolerance=error_bound_tolerance(absolute_eb)
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"zfp违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    return {"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size,"compression_time":compression_time,"decompression_time":decompression_time}

def cleanup_test_outputs(task,compressor):
    suffixes={
        "asz":(".asz",".bin"),
        "sz3":(".sz3",".sz3.bin"),
        "qoz":(".qoz",".qoz.bin"),
        "zfp":(".zfp",".zfp.bin"),
        "sperr":(".sperr",".sperr.bin"),
    }
    for suffix in suffixes[compressor]:
        output_path=codec_output_path(task,suffix)
        if output_path.is_file():
            output_path.unlink()
            print(f"删除运行产物：{output_path}",flush=True)

def run_sperr(task,rel_eb,value_range):
    data_path=task["data_path"]
    shape=task["data_shape"]
    compressed_path=codec_output_path(task,".sperr")
    decompressed_path=codec_output_path(task,".sperr.bin")
    absolute_eb=rel_eb*value_range
    executable=project_root/"install/sperr_install/bin/sperr3d"
    dimensions=["--dims",shape[2],shape[1],shape[0]]
    absolute_eb_text=f"{absolute_eb:.17g}"
    compression_output=run_command([executable,data_path,"-c","--ftype","32",*dimensions,"--bitstream",compressed_path,"--pwe",absolute_eb_text],silent=True)
    decompression_output=run_command([executable,compressed_path,"-d","--ftype","32",*dimensions,"--decomp_f",decompressed_path,"--pwe",absolute_eb_text],silent=True)
    compression_time=parse_codec_time(compression_output,"sperr","compression")
    decompression_time=parse_codec_time(decompression_output,"sperr","decompression")
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,decompressed_path)
    tolerance=error_bound_tolerance(absolute_eb)
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"sperr违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    return {"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size,"compression_time":compression_time,"decompression_time":decompression_time}

def report_result(method_name,task,rel_eb,result,write_csv):
    data_path=task["data_path"]
    time_text=""
    if "compression_time" in result:
        time_text=f",compression_time={result['compression_time']},decompression_time={result['decompression_time']}"
    if "data_range_time" in result:
        time_text+=f",data_range_time={result['data_range_time']}"
    if "generate_config_time" in result:
        time_text+=f",generate_config_time={result['generate_config_time']}"
    if "get_default_slope_time" in result:
        time_text+=f",get_default_slope_time={result['get_default_slope_time']}"
    if "preprocessing_time" in result:
        time_text+=f",preprocessing_time={result['preprocessing_time']}"
    audit_text=""
    if "max_error" in result:
        audit_text=f",max_error={result['max_error']},absolute_eb={result['absolute_eb']},compressed_bytes={result['compressed_bytes']}"
    print(f"result method={method_name},rel_eb={rel_eb:g},cr={result['cr']},br={result['br']},psnr={result['psnr']}{audit_text}{time_text}",flush=True)
    if write_csv:
        csv_path=codec_output_path(task,".csv")
        write_csv_item(csv_path,{"REL_EB":rel_eb},method_name.upper()+"_BR",result["br"])
        write_csv_item(csv_path,{"REL_EB":rel_eb},method_name.upper()+"_PSNR",result["psnr"])

def prepare_runtime_methods(methods,data_path):
    runtime_methods=[]
    for method in methods:
        runtime_method=dict(method)
        if "read_plan" in method:
            runtime_method["read_plan"]=resolve_plan_path(method["read_plan"],data_path)
            runtime_method["plans"]=load_plan(runtime_method["read_plan"])
        if "write_plan" in method:
            runtime_method["write_plan"]=resolve_plan_path(method["write_plan"],data_path)
            runtime_method["written_plans"]={}
        runtime_methods.append(runtime_method)
    return runtime_methods

def run_task(task,data_path,write_csv,asz_bin_directory):
    validate_data_file(data_path,task["data_shape"])
    data_task={**task,"data_path":data_path}
    if data_task.get("output_directory") is not None:
        data_task["output_directory"].mkdir(parents=True,exist_ok=True)
    runtime_methods=prepare_runtime_methods(task["method_list"],data_path)
    value_range=None
    if any(method["compressor"] in ("zfp","sperr") for method in runtime_methods):
        value_range=calculate_float32_range(data_path)
    records=[]
    for rel_eb in task["rel_eb_list"]:
        for method in runtime_methods:
            method_name=method["name"]
            compressor=method["compressor"]
            print(f"开始：method={method_name},compressor={compressor},data={data_path},rel_eb={rel_eb:g}",flush=True)
            try:
                if compressor=="asz":
                    plan_predictor_family=None
                    if "read_plan" not in method:
                        predictors=None
                    else:
                        predictors,plan_predictor_family=predictors_for_rel_eb(method["plans"],rel_eb,method["read_plan"])
                    result,actual_predictors,actual_predictor_family=run_asz(data_task,rel_eb,predictors,method,asz_bin_directory,plan_predictor_family)
                    if "write_plan" in method:
                        method["written_plans"][rel_eb]=(actual_predictors,actual_predictor_family)
                elif compressor in ("sz3","qoz"):
                    result=run_sz_variant(compressor,data_task,rel_eb)
                elif compressor=="zfp":
                    result=run_zfp(data_task,rel_eb,value_range)
                else:
                    result=run_sperr(data_task,rel_eb,value_range)
                report_result(method_name,data_task,rel_eb,result,write_csv)
                records.append({"data_path":str(data_path),"rel_eb":rel_eb,"method":method_name,**result})
            finally:
                if task.get("cleanup_after_each_test",False):
                    cleanup_test_outputs(data_task,compressor)
    for method in runtime_methods:
        if "write_plan" in method:
            write_plan(method["write_plan"],method["written_plans"])
    return records

def write_comparison_summary(path,records,baseline_method):
    baselines={(record["data_path"],record["rel_eb"]):record for record in records if record["method"]==baseline_method}
    missing={(record["data_path"],record["rel_eb"]) for record in records}-baselines.keys()
    if missing:
        raise RuntimeError(f"汇总结果缺少{len(missing)}个{baseline_method}基准")
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary_path=path.with_name(path.name+".tmp")
    with open(temporary_path,"w",newline="",encoding="utf-8") as summary_file:
        fieldnames=["DATA_PATH","REL_EB","METHOD","CR","BR","PSNR","MAX_ERROR","ABSOLUTE_EB","COMPRESSED_BYTES","CR_DROP_PERCENT","PREPROCESSING_TIME","GET_DEFAULT_SLOPE_TIME","GENERATE_CONFIG_TIME","PREDICTOR_FAMILY_SELECTION_TIME","DATA_RANGE_TIME","COMPRESSION_TIME","DECOMPRESSION_TIME","DEFAULT_SLOPE","DEFAULT_SLOPE_MAX_INVALID_RATIO","DEFAULT_SLOPE_FALLBACK_USED","DEFAULT_SLOPE_FALLBACK_REASON","PREDICTOR_FAMILY","PREDICTOR_FAMILY_SELECTOR","PREDICTOR_FAMILY_DIRECTION","PREDICTOR_FAMILY_SAMPLES","PREDICTOR_FAMILY_BLOCKS","PREDICTOR_FAMILY_SAMPLED_BLOCK_POINTS","PREDICTOR_FAMILY_SAMPLE_POINT_BUDGET","PREDICTOR_FAMILY_PROBE_BLOCK_PIVOT_RATIO","PREDICTOR_FAMILY_FALLBACK","CUBIC_MSE","QUINTIC_MSE","CUBIC_PSNR","QUINTIC_PSNR","CUBIC_H1","QUINTIC_H1","SIX_SCORE_GAIN","T_HISTOGRAM","T_FALLBACK_COUNT"]
        writer=csv.DictWriter(summary_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        for record in records:
            baseline_cr=baselines[(record["data_path"],record["rel_eb"])]["cr"]
            writer.writerow({"DATA_PATH":record["data_path"],"REL_EB":record["rel_eb"],"METHOD":record["method"],"CR":record["cr"],"BR":record["br"],"PSNR":record["psnr"],"MAX_ERROR":record.get("max_error",""),"ABSOLUTE_EB":record.get("absolute_eb",""),"COMPRESSED_BYTES":record.get("compressed_bytes",""),"CR_DROP_PERCENT":100*(baseline_cr-record["cr"])/baseline_cr,"PREPROCESSING_TIME":record.get("preprocessing_time",""),"GET_DEFAULT_SLOPE_TIME":record.get("get_default_slope_time",""),"GENERATE_CONFIG_TIME":record.get("generate_config_time",""),"PREDICTOR_FAMILY_SELECTION_TIME":record.get("predictor_family_selection_time",""),"DATA_RANGE_TIME":record.get("data_range_time",""),"COMPRESSION_TIME":record.get("compression_time",""),"DECOMPRESSION_TIME":record.get("decompression_time",""),"DEFAULT_SLOPE":record.get("default_slope",""),"DEFAULT_SLOPE_MAX_INVALID_RATIO":record.get("default_slope_max_invalid_ratio",""),"DEFAULT_SLOPE_FALLBACK_USED":record.get("default_slope_fallback_used",""),"DEFAULT_SLOPE_FALLBACK_REASON":record.get("default_slope_fallback_reason",""),"PREDICTOR_FAMILY":record.get("predictor_family",""),"PREDICTOR_FAMILY_SELECTOR":record.get("predictor_family_selector",""),"PREDICTOR_FAMILY_DIRECTION":record.get("predictor_family_direction",""),"PREDICTOR_FAMILY_SAMPLES":record.get("predictor_family_samples",""),"PREDICTOR_FAMILY_BLOCKS":record.get("predictor_family_blocks",""),"PREDICTOR_FAMILY_SAMPLED_BLOCK_POINTS":record.get("predictor_family_sampled_block_points",""),"PREDICTOR_FAMILY_SAMPLE_POINT_BUDGET":record.get("predictor_family_sample_point_budget",""),"PREDICTOR_FAMILY_PROBE_BLOCK_PIVOT_RATIO":record.get("predictor_family_probe_block_pivot_ratio",""),"PREDICTOR_FAMILY_FALLBACK":record.get("predictor_family_fallback",""),"CUBIC_MSE":record.get("cubic_mse",""),"QUINTIC_MSE":record.get("quintic_mse",""),"CUBIC_PSNR":record.get("cubic_psnr",""),"QUINTIC_PSNR":record.get("quintic_psnr",""),"CUBIC_H1":record.get("cubic_h1",""),"QUINTIC_H1":record.get("quintic_h1",""),"SIX_SCORE_GAIN":record.get("six_score_gain",""),"T_HISTOGRAM":record.get("t_histogram",""),"T_FALLBACK_COUNT":record.get("t_fallback_count","")})
    os.replace(temporary_path,path)
    print(f"写入比较汇总：{path}",flush=True)

def cli():
    parser=argparse.ArgumentParser(description="默认依次编译、安装、运行configs目录中的ASZ及基线压缩器实验，每一步都可以单独关掉",allow_abbrev=False)
    parser.add_argument("config",nargs="?",help="configs中的配置名称，或配置文件路径。加了--no-run时可以不给，这时只编译ASZ，并装到install")
    parser.add_argument("--no-build",action="store_true",help="不编译。默认编译并安装config用到的baseline，再把ASZ编译到build")
    parser.add_argument("--no-install",action="store_true",help="不安装。默认把build里的ASZ装到config的install_dir，没写时装到install")
    parser.add_argument("--no-run",action="store_true",help="不运行实验。默认用安装目录里的ASZ和install/*_install里的baseline运行config中的task")
    parser.add_argument("--submit",action="store_true",help="当前机器上什么都不做，把去掉--submit的同一条命令按config中slurm的资源提交成Slurm作业。日志写到results/slurm")
    parser.add_argument("--silent-build",action="store_true",help="隐藏成功的构建输出")
    parser.add_argument("--no-csv",action="store_true",help="不写入数据文件旁的CSV")
    arguments=parser.parse_args()
    config=None
    if arguments.config is not None:
        config_path=resolve_config_path(arguments.config,config_directory)
        config=load_config(config_path)
    elif not arguments.no_run or arguments.submit:
        parser.error("运行实验或提交作业时必须给config")
    if arguments.submit:
        if config.slurm is None:
            parser.error(f"{config_path}里没有slurm，不能提交作业。需要提交时，在config顶层加上\"slurm\":{{...}}")
        # 隐藏的config（例如.final18_rd_small.json）去掉开头的点作为作业名，日志就不是隐藏文件
        submit_slurm_job(job_command_from_argv(),config.slurm,job_name=Path(config_path).stem.lstrip("."),output_path=slurm_log_path,account=slurm_account)
        return
    install_dir=Path(resolve_install_dir(None,project_root) if config is None else config.install_dir)
    compressors=[] if config is None else list(dict.fromkeys(method["compressor"] for task in config.tasks for method in task["method_list"]))
    if not arguments.no_build:
        build_project([compressor for compressor in compressors if compressor!="asz"],get_max_cpus(8),arguments.silent_build)
    if not arguments.no_install:
        install_project(install_dir,arguments.silent_build)
    if arguments.no_run:
        return
    asz_bin_directory=install_dir/"bin"
    if "asz" in compressors:
        for name in ("s1_compress","s1_decompress"):
            if not (asz_bin_directory/name).is_file():
                raise FileNotFoundError(f"找不到{asz_bin_directory/name}，请先编译并安装到这个目录")
    for task in config.tasks:
        records=[]
        for data_path in task["data_path_list"]:
            records.extend(run_task(task,data_path,not arguments.no_csv,asz_bin_directory))
            if task.get("summary_csv") is not None:
                write_comparison_summary(task["summary_csv"],records,task["comparison_baseline"])

if __name__=="__main__":
    cli()
