import argparse,array,csv,errno,json,math,os,pty,re,shlex,subprocess,sys
from pathlib import Path

import numpy as np

from add_csv import add_csv

project_root=Path(__file__).resolve().parent
config_directory=project_root/"configs"
asz_executable_directory=Path(os.environ.get("ASZ_EXECUTABLE_DIRECTORY",project_root/"install/bin")).resolve()
supported_compressors=("asz","sz3","qoz","zfp","sperr")
traversal_orders={(1,2,0):"120",(0,2,1):"021",(0,1,2):"012"}
asz_parameter_keys=("pivot_eb_ratio","eb_ratio","slope_ratio","block_pivot_ratio","max_layer_num","full_predictor_search_layer_num")
asz_compress_parameter_keys=("generate_config_sample_stride","h1_block_sampling_num","stat_eb_ratio")
asz_block_policy_keys=("coarse_block_pivot_ratio","fine_block_pivot_ratio")

def run_command(command,silent=False,dry_run=False):
    command=[str(item) for item in command]
    print(f"$ {shlex.join(command)}",flush=True)
    if dry_run:
        return ""
    if silent:
        result=subprocess.run(command,capture_output=True,text=True,encoding="utf-8")
        if result.returncode!=0:
            if result.stdout:
                print(result.stdout,end="")
            if result.stderr:
                print(result.stderr,end="",file=sys.stderr)
            raise subprocess.CalledProcessError(result.returncode,command)
        return result.stdout+result.stderr
    master,slave=pty.openpty()
    process=subprocess.Popen(command,stdout=slave,stderr=slave,text=True,bufsize=1)
    os.close(slave)
    lines=[]
    with os.fdopen(master) as process_stdout:
        try:
            for line in process_stdout:
                print(line,end="")
                lines.append(line)
        except OSError as error:
            if error.errno!=errno.EIO:
                raise
    process.wait()
    if process.returncode!=0:
        raise subprocess.CalledProcessError(process.returncode,command)
    return "".join(lines)

def resolve_json_path(path_or_name):
    path=Path(path_or_name).expanduser()
    if path.is_absolute() or path.parent!=Path("."):
        resolved=path.resolve()
    else:
        filename=path.name if path.suffix==".json" else path.name+".json"
        resolved=(config_directory/filename).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"找不到JSON配置：{resolved}")
    return resolved

def resolve_task_path(path):
    expanded=Path(path).expanduser()
    return expanded.resolve() if expanded.is_absolute() else (project_root/expanded).resolve()

def resolve_data_path(path):
    expanded=Path(path).expanduser()
    absolute=expanded if expanded.is_absolute() else project_root/expanded
    return Path(os.path.abspath(absolute))

def prepare_methods(method_list,task_id):
    if not isinstance(method_list,list) or not method_list:
        raise ValueError(f"task {task_id}的method_list必须是非空列表")
    methods=[]
    for method_id,method in enumerate(method_list):
        if isinstance(method,str):
            prepared={"name":method,"compressor":method}
        elif isinstance(method,dict):
            allowed_keys={"name","compressor","read_plan","write_plan","predictor_family","t_policy",*asz_parameter_keys,*asz_compress_parameter_keys,*asz_block_policy_keys}
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
        if "t_policy" in prepared:
            if prepared["compressor"]!="asz" or prepared["t_policy"] not in ("adaptive","fixed_4_16","fixed_5_16"):
                raise ValueError(f"task {task_id}的method {method_id}的t_policy只能是adaptive、fixed_4_16或fixed_5_16且只能用于asz")
        for key in (*asz_parameter_keys,*asz_compress_parameter_keys):
            if key not in prepared:
                continue
            value=prepared[key]
            if prepared["compressor"]!="asz":
                raise ValueError(f"task {task_id}的method {method_id}只有asz可以设置{key}")
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError(f"task {task_id}的method {method_id}的{key}必须是有限数字")
            if key in ("block_pivot_ratio","max_layer_num","full_predictor_search_layer_num","generate_config_sample_stride","h1_block_sampling_num"):
                if not isinstance(value,int) or value<=0:
                    raise ValueError(f"task {task_id}的method {method_id}的{key}必须是正整数")
                if key in ("max_layer_num","full_predictor_search_layer_num") and value>63:
                    raise ValueError(f"task {task_id}的method {method_id}的{key}不能超过63")
            elif not 0<value<=1:
                raise ValueError(f"task {task_id}的method {method_id}的{key}必须在(0,1]内")
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

def load_tasks(json_path):
    with open(json_path,encoding="utf-8") as config_file:
        tasks=json.load(config_file)
    if not isinstance(tasks,list):
        raise TypeError("JSON顶层必须是task list")
    if not tasks:
        raise ValueError("JSON中没有task")
    required_keys={"data_path_list","data_shape","rel_eb_list","method_list"}
    allowed_keys=required_keys|{"cleanup_after_each_test","comparison_baseline","summary_csv"}
    prepared=[]
    for task_id,task in enumerate(tasks):
        if not isinstance(task,dict):
            raise TypeError(f"task {task_id}必须是object")
        missing=required_keys-task.keys()
        if missing:
            raise ValueError(f"task {task_id}缺少参数：{','.join(sorted(missing))}")
        unknown=task.keys()-allowed_keys
        if unknown:
            raise ValueError(f"task {task_id}包含未知参数：{','.join(sorted(unknown))}")
        data_path_list=task["data_path_list"]
        if not isinstance(data_path_list,list) or not data_path_list or any(not isinstance(path,str) or not path for path in data_path_list):
            raise ValueError(f"task {task_id}的data_path_list必须是非空字符串列表")
        if len(data_path_list)!=len(set(data_path_list)):
            raise ValueError(f"task {task_id}的data_path_list不能包含重复项")
        shape=task["data_shape"]
        if not isinstance(shape,list) or len(shape)!=3 or any(not isinstance(value,int) or value<=0 for value in shape):
            raise ValueError(f"task {task_id}的data_shape必须包含三个正整数")
        rel_eb_list=task["rel_eb_list"]
        if not isinstance(rel_eb_list,list) or not rel_eb_list or any(not isinstance(value,(int,float)) or value<=0 for value in rel_eb_list):
            raise ValueError(f"task {task_id}的rel_eb_list必须是非空正数列表")
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
        if task.get("summary_csv") is not None and not isinstance(task["summary_csv"],str):
            raise ValueError(f"task {task_id}的summary_csv必须是字符串")
        if len(data_path_list)>1:
            for method in methods:
                if "write_plan" in method and "{stem}" not in method["write_plan"] and "{name}" not in method["write_plan"]:
                    raise ValueError(f"task {task_id}有多个数据文件，method {method['name']}的write_plan必须包含{{stem}}或{{name}}")
        prepared_task={**task,"data_path_list":[resolve_data_path(path) for path in data_path_list],"rel_eb_list":[float(value) for value in rel_eb_list],"method_list":methods}
        if prepared_task.get("summary_csv") is not None:
            prepared_task["summary_csv"]=resolve_task_path(prepared_task["summary_csv"])
        prepared.append(prepared_task)
    return prepared

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

def build_asz(silent,dry_run):
    run_command(["cmake","-S",project_root/"c_codes","-B",project_root/"build","-DCODE_NAME=s1_compress",f"-DCMAKE_INSTALL_PREFIX={project_root/'install'}"],silent,dry_run)
    run_command(["cmake","--build",project_root/"build","--parallel","4"],silent,dry_run)
    run_command(["cmake","--install",project_root/"build"],silent,dry_run)

def build_zstd(silent,dry_run):
    build_path=project_root/"build/common_zstd_build"
    install_path=project_root/"install/common_zstd_install"
    run_command(["cmake","-S",project_root/"third_party/zstd/build/cmake","-B",build_path,"-DCMAKE_BUILD_TYPE=Release","-DCMAKE_INSTALL_LIBDIR=lib","-DZSTD_BUILD_SHARED=OFF","-DZSTD_BUILD_STATIC=ON","-DZSTD_BUILD_PROGRAMS=OFF","-DZSTD_BUILD_TESTS=OFF",f"-DCMAKE_INSTALL_PREFIX={install_path}"],silent,dry_run)
    run_command(["cmake","--build",build_path,"--parallel","4"],silent,dry_run)
    run_command(["cmake","--install",build_path],silent,dry_run)

def zstd_cmake_environment():
    pkgconfig_path=project_root/"install/common_zstd_install/lib/pkgconfig"
    return ["cmake","-E","env",f"PKG_CONFIG_PATH={pkgconfig_path}","cmake"]

def zstd_cmake_library():
    return f"-Dpkgcfg_lib_ZSTD_zstd:FILEPATH={project_root/'install/common_zstd_install/lib/libzstd.a'}"

def build_sz3(silent,dry_run):
    build_path=project_root/"build/sz3_build"
    install_path=project_root/"install/sz3_install"
    run_command([*zstd_cmake_environment(),"-S",project_root/"third_party/SZ3","-B",build_path,"-UZSTD_*",zstd_cmake_library(),"-DBUILD_SHARED_LIBS=OFF","-DSZ3_USE_BUNDLED_ZSTD=OFF",f"-DCMAKE_INSTALL_PREFIX={install_path}"],silent,dry_run)
    run_command(["cmake","--build",build_path,"--parallel","4"],silent,dry_run)
    run_command(["cmake","--install",build_path],silent,dry_run)

def build_qoz(silent,dry_run):
    build_path=project_root/"build/qoz_build"
    install_path=project_root/"install/qoz_install"
    run_command([*zstd_cmake_environment(),"-S",project_root/"third_party/QoZ","-B",build_path,"-UZSTD_*",zstd_cmake_library(),"-DBUILD_SHARED_LIBS=OFF","-DQoZ_USE_BUNDLED_ZSTD=OFF","-DQoZ_DEBUG_TIMINGS=OFF",f"-DCMAKE_INSTALL_PREFIX={install_path}"],silent,dry_run)
    run_command(["cmake","--build",build_path,"--parallel","4"],silent,dry_run)
    run_command(["cmake","--install",build_path],silent,dry_run)

def build_zfp(silent,dry_run):
    build_path=project_root/"build/zfp_build"
    install_path=project_root/"install/zfp_install"
    run_command(["cmake","-S",project_root/"third_party/zfp","-B",build_path,"-DBUILD_SHARED_LIBS=OFF",f"-DCMAKE_INSTALL_PREFIX={install_path}"],silent,dry_run)
    run_command(["cmake","--build",build_path,"--parallel","4"],silent,dry_run)
    run_command(["cmake","--install",build_path],silent,dry_run)

def build_sperr(silent,dry_run):
    build_path=project_root/"build/sperr_build"
    install_path=project_root/"install/sperr_install"
    run_command(["cmake","-S",project_root/"third_party/sperr","-B",build_path,"-DBUILD_SHARED_LIBS=OFF",f"-DCMAKE_INSTALL_PREFIX={install_path}"],silent,dry_run)
    run_command(["cmake","--build",build_path,"--parallel","4"],silent,dry_run)
    run_command(["cmake","--install",build_path],silent,dry_run)

def build_compressors(compressors,silent,dry_run):
    if any(compressor in ("sz3","qoz") for compressor in compressors):
        build_zstd(silent,dry_run)
    for compressor in compressors:
        if compressor=="asz":
            build_asz(silent,dry_run)
        elif compressor=="sz3":
            build_sz3(silent,dry_run)
        elif compressor=="qoz":
            build_qoz(silent,dry_run)
        elif compressor=="zfp":
            build_zfp(silent,dry_run)
        elif compressor=="sperr":
            build_sperr(silent,dry_run)

def parse_asz_result(output):
    patterns={"cr":r"^CR= ([0-9.eE+-]+)\r?$","br":r"^BR= ([0-9.eE+-]+)\r?$","psnr":r"^PSNR= ([0-9.eE+-]+)","compression_time":r"^Compression time: ([0-9.eE+-]+)","decompression_time":r"^Decompression time: ([0-9.eE+-]+)"}
    result={}
    for key,pattern in patterns.items():
        matches=re.findall(pattern,output,re.MULTILINE)
        if not matches:
            raise RuntimeError(f"未能解析ASZ的{key}")
        result[key]=float(matches[-1])
    matches=re.findall(r"^Generate config time: ([0-9.eE+-]+)",output,re.MULTILINE)
    if matches:
        result["generate_config_time"]=float(matches[-1])
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

def run_asz(task,rel_eb,predictors,method,dry_run,plan_predictor_family=None):
    shape=task["data_shape"]
    data_path=task["data_path"]
    compressed_path=Path(str(data_path)+".asz")
    reconstructed_path=Path(str(data_path)+".bin")
    common=["-f","-i",data_path,"-3",*shape,"-M","REL",f"{rel_eb:.17g}"]
    option_names={"pivot_eb_ratio":"--pivot-eb-ratio","eb_ratio":"--eb-ratio","slope_ratio":"--slope-ratio","block_pivot_ratio":"--block-pivot-ratio","max_layer_num":"--max-layer-num","full_predictor_search_layer_num":"--full-predictor-search-layer-num","generate_config_sample_stride":"--generate-config-sample-stride","h1_block_sampling_num":"--h1-block-sampling-num","stat_eb_ratio":"--stat-eb-ratio"}
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
    if "t_policy" in method_options:
        common.extend(["--t-policy",method_options["t_policy"]])
    compress_command=[asz_executable_directory/"s1_compress",*common]
    for key in asz_compress_parameter_keys:
        if key in method_options:
            compress_command.extend([option_names[key],method_options[key]])
    if predictors is not None:
        compress_command.extend(["--predictor-plan",",".join(predictors)])
    compression_output=run_command(compress_command,dry_run=dry_run)
    decompression_output=run_command([asz_executable_directory/"s1_decompress",*common],dry_run=dry_run)
    if dry_run:
        return None,None,None
    output=compression_output+decompression_output
    reported=parse_asz_result(output)
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,reconstructed_path)
    absolute_eb=rel_eb*metrics["value_range"]
    tolerance=max(1.0,metrics["value_range"])*1e-12
    if metrics["max_error"]>absolute_eb*1.01+tolerance:
        raise RuntimeError(f"asz违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    if not math.isclose(reported["cr"],cr,rel_tol=1e-5,abs_tol=1e-6):
        raise RuntimeError(f"asz报告的CR与压缩文件不一致：reported={reported['cr']},actual={cr}")
    result={"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size,"compression_time":reported["compression_time"],"decompression_time":reported["decompression_time"]}
    if "generate_config_time" in reported:
        result["generate_config_time"]=reported["generate_config_time"]
    return result,parse_predictors(compression_output),parse_predictor_family(compression_output)

def run_sz_variant(compressor,task,rel_eb,dry_run):
    data_path=task["data_path"]
    shape=task["data_shape"]
    compressed_path=Path(str(data_path)+f".{compressor}")
    reconstructed_path=Path(str(data_path)+f".{compressor}.bin")
    executable=project_root/f"install/{compressor}_install/bin"/("sz3" if compressor=="sz3" else "qoz")
    command=[executable,"-f","-i",data_path,"-z",compressed_path,"-o",reconstructed_path,"-3",shape[2],shape[1],shape[0],"-M","REL",f"{rel_eb:.17g}","-a"]
    if compressor=="qoz":
        command.extend(["-q","4"])
    output=run_command(command,silent=True,dry_run=dry_run)
    if dry_run:
        return None
    reported=parse_sz_result(output,compressor)
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,reconstructed_path)
    absolute_eb=rel_eb*metrics["value_range"]
    tolerance=absolute_eb*1e-5+max(1.0,metrics["value_range"])*1e-12
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"{compressor}违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    if not math.isclose(reported["cr"],cr,rel_tol=1e-5,abs_tol=1e-6):
        raise RuntimeError(f"{compressor}报告的CR与压缩文件不一致：reported={reported['cr']},actual={cr}")
    if not math.isclose(reported["psnr"],metrics["psnr"],rel_tol=1e-7,abs_tol=1e-5):
        raise RuntimeError(f"{compressor}报告的PSNR与独立计算不一致：reported={reported['psnr']},actual={metrics['psnr']}")
    return {"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size,"compression_time":reported["compression_time"],"decompression_time":reported["decompression_time"]}

def run_zfp(task,rel_eb,value_range,dry_run):
    data_path=task["data_path"]
    shape=task["data_shape"]
    compressed_path=Path(str(data_path)+".zfp")
    decompressed_path=Path(str(data_path)+".zfp.bin")
    absolute_eb=rel_eb*value_range if value_range is not None else f"<{rel_eb:.17g}*data_range>"
    executable=project_root/"install/zfp_install/bin/zfp"
    dimensions=["-3",shape[2],shape[1],shape[0]]
    absolute_eb_text=f"{absolute_eb:.17g}" if isinstance(absolute_eb,float) else absolute_eb
    run_command([executable,"-f","-i",data_path,"-z",compressed_path,*dimensions,"-a",absolute_eb_text],silent=True,dry_run=dry_run)
    run_command([executable,"-f","-z",compressed_path,"-o",decompressed_path,*dimensions,"-a",absolute_eb_text],silent=True,dry_run=dry_run)
    if dry_run:
        return None
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,decompressed_path)
    tolerance=absolute_eb*1e-5+max(1.0,value_range)*1e-12
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"zfp违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    return {"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size}

def cleanup_test_outputs(data_path,compressor):
    suffixes={
        "asz":(".asz",".bin"),
        "sz3":(".sz3",".sz3.bin"),
        "qoz":(".qoz",".qoz.bin"),
        "zfp":(".zfp",".zfp.bin"),
        "sperr":(".sperr",".sperr.bin"),
    }
    for suffix in suffixes[compressor]:
        output_path=Path(str(data_path)+suffix)
        if output_path.is_file():
            output_path.unlink()
            print(f"删除运行产物：{output_path}",flush=True)

def run_sperr(task,rel_eb,value_range,dry_run):
    data_path=task["data_path"]
    shape=task["data_shape"]
    compressed_path=Path(str(data_path)+".sperr")
    decompressed_path=Path(str(data_path)+".sperr.bin")
    absolute_eb=rel_eb*value_range if value_range is not None else f"<{rel_eb:.17g}*data_range>"
    executable=project_root/"install/sperr_install/bin/sperr3d"
    dimensions=["--dims",shape[2],shape[1],shape[0]]
    absolute_eb_text=f"{absolute_eb:.17g}" if isinstance(absolute_eb,float) else absolute_eb
    run_command([executable,data_path,"-c","--ftype","32",*dimensions,"--bitstream",compressed_path,"--pwe",absolute_eb_text],silent=True,dry_run=dry_run)
    run_command([executable,compressed_path,"-d","--ftype","32",*dimensions,"--decomp_f",decompressed_path,"--pwe",absolute_eb_text],silent=True,dry_run=dry_run)
    if dry_run:
        return None
    compressed_size=compressed_path.stat().st_size
    if compressed_size<=0:
        raise RuntimeError(f"压缩文件为空：{compressed_path}")
    cr=data_path.stat().st_size/compressed_size
    metrics=calculate_float32_metrics(data_path,decompressed_path)
    tolerance=absolute_eb*1e-5+max(1.0,value_range)*1e-12
    if metrics["max_error"]>absolute_eb+tolerance:
        raise RuntimeError(f"sperr违反误差界：max_error={metrics['max_error']},absolute_eb={absolute_eb}")
    return {"cr":cr,"br":32/cr,"psnr":metrics["psnr"],"max_error":metrics["max_error"],"absolute_eb":absolute_eb,"compressed_bytes":compressed_size}

def report_result(method_name,data_path,rel_eb,result,write_csv):
    time_text=""
    if "compression_time" in result:
        time_text=f",compression_time={result['compression_time']},decompression_time={result['decompression_time']}"
    if "generate_config_time" in result:
        time_text+=f",generate_config_time={result['generate_config_time']}"
    audit_text=""
    if "max_error" in result:
        audit_text=f",max_error={result['max_error']},absolute_eb={result['absolute_eb']},compressed_bytes={result['compressed_bytes']}"
    print(f"result method={method_name},rel_eb={rel_eb:g},cr={result['cr']},br={result['br']},psnr={result['psnr']}{audit_text}{time_text}",flush=True)
    if write_csv:
        add_csv(method_name,str(data_path)+".csv",rel_eb,result["br"],result["psnr"])

def prepare_runtime_methods(methods,data_path,dry_run):
    runtime_methods=[]
    for method in methods:
        runtime_method=dict(method)
        if "read_plan" in method:
            runtime_method["read_plan"]=resolve_plan_path(method["read_plan"],data_path)
            if not dry_run or runtime_method["read_plan"].is_file():
                runtime_method["plans"]=load_plan(runtime_method["read_plan"])
            else:
                runtime_method["plans"]=None
        if "write_plan" in method:
            runtime_method["write_plan"]=resolve_plan_path(method["write_plan"],data_path)
            runtime_method["written_plans"]={}
        runtime_methods.append(runtime_method)
    return runtime_methods

def run_task(task,data_path,dry_run,write_csv):
    validate_data_file(data_path,task["data_shape"])
    data_task={**task,"data_path":data_path}
    runtime_methods=prepare_runtime_methods(task["method_list"],data_path,dry_run)
    value_range=None
    if any(method["compressor"] in ("zfp","sperr") for method in runtime_methods) and not dry_run:
        value_range=calculate_float32_range(data_path)
    records=[]
    for rel_eb in task["rel_eb_list"]:
        for method in runtime_methods:
            method_name=method["name"]
            compressor=method["compressor"]
            print(f"开始：method={method_name},compressor={compressor},data={data_path},rel_eb={rel_eb:g}",flush=True)
            if compressor=="asz":
                plan_predictor_family=None
                if "read_plan" not in method:
                    predictors=None
                elif method["plans"] is None:
                    predictors=[f"<from-plan:{method['read_plan']}>"]
                else:
                    predictors,plan_predictor_family=predictors_for_rel_eb(method["plans"],rel_eb,method["read_plan"])
                result,actual_predictors,actual_predictor_family=run_asz(data_task,rel_eb,predictors,method,dry_run,plan_predictor_family)
                if actual_predictors is not None and "write_plan" in method:
                    method["written_plans"][rel_eb]=(actual_predictors,actual_predictor_family)
            elif compressor in ("sz3","qoz"):
                result=run_sz_variant(compressor,data_task,rel_eb,dry_run)
            elif compressor=="zfp":
                result=run_zfp(data_task,rel_eb,value_range,dry_run)
            else:
                result=run_sperr(data_task,rel_eb,value_range,dry_run)
            if result is not None:
                report_result(method_name,data_path,rel_eb,result,write_csv)
                records.append({"data_path":str(data_path),"rel_eb":rel_eb,"method":method_name,**result})
                if task.get("cleanup_after_each_test",False):
                    cleanup_test_outputs(data_path,compressor)
    if not dry_run:
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
        fieldnames=["DATA_PATH","REL_EB","METHOD","CR","BR","PSNR","CR_DROP_PERCENT","GENERATE_CONFIG_TIME","COMPRESSION_TIME","DECOMPRESSION_TIME"]
        writer=csv.DictWriter(summary_file,fieldnames=fieldnames,lineterminator="\n")
        writer.writeheader()
        for record in records:
            baseline_cr=baselines[(record["data_path"],record["rel_eb"])]["cr"]
            writer.writerow({"DATA_PATH":record["data_path"],"REL_EB":record["rel_eb"],"METHOD":record["method"],"CR":record["cr"],"BR":record["br"],"PSNR":record["psnr"],"CR_DROP_PERCENT":100*(baseline_cr-record["cr"])/baseline_cr,"GENERATE_CONFIG_TIME":record.get("generate_config_time",""),"COMPRESSION_TIME":record.get("compression_time",""),"DECOMPRESSION_TIME":record.get("decompression_time","")})
    os.replace(temporary_path,path)
    print(f"写入比较汇总：{path}",flush=True)

def cli():
    parser=argparse.ArgumentParser(description="运行configs目录中的ASZ及基线压缩器实验")
    parser.add_argument("json",help="configs中的JSON配置名称，或JSON文件路径")
    parser.add_argument("--skip-build",action="store_true",help="使用已有安装，不重新构建")
    parser.add_argument("--silent-build",action="store_true",help="隐藏成功的构建输出")
    parser.add_argument("--dry-run",action="store_true",help="只校验配置并打印命令")
    parser.add_argument("--no-csv",action="store_true",help="不写入数据文件旁的CSV")
    arguments=parser.parse_args()
    try:
        tasks=load_tasks(resolve_json_path(arguments.json))
        compressors=list(dict.fromkeys(method["compressor"] for task in tasks for method in task["method_list"]))
        if not arguments.skip_build and not arguments.dry_run:
            build_compressors(compressors,arguments.silent_build,False)
        for task in tasks:
            records=[]
            for data_path in task["data_path_list"]:
                records.extend(run_task(task,data_path,arguments.dry_run,not arguments.no_csv))
                if task.get("summary_csv") is not None and not arguments.dry_run:
                    write_comparison_summary(task["summary_csv"],records,task["comparison_baseline"])
    except (FileNotFoundError,TypeError,ValueError) as error:
        parser.error(str(error))

if __name__=="__main__":
    cli()
