import argparse,errno,os,pty,shlex,subprocess
from pathlib import Path

project_root=Path(__file__).resolve().parent
code_name_map={
    2:"s2_many_prediction",
    3:"s3_conclude_sp_result",
    4:"s4_verify_sp_proxy",
    5:"s5_conclude_coeff_result",
    6:"s6_quantic_prediction",
    7:"s7_find_best_t2_per_eb",
    8:"s8_get_AB_distribution",
}

def run_command(command,silent=False):
    command=[str(item) for item in command]
    print(f"$ {shlex.join(command)}",flush=True)
    if silent:
        result=subprocess.run(command,capture_output=True,text=True,encoding="utf-8")
        if result.returncode!=0:
            print(result.stdout,end="")
            print(result.stderr,end="")
            raise subprocess.CalledProcessError(result.returncode,command)
        return result.stdout+result.stderr
    master,slave=pty.openpty()
    process=subprocess.Popen(command,stdout=slave,stderr=slave,text=True,bufsize=1,cwd=project_root)
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

def resolve_code_name(value):
    try:
        number=int(value)
    except ValueError:
        number=None
    if number in code_name_map:
        return code_name_map[number]
    if value in code_name_map.values():
        return value
    choices=", ".join(f"{number}={name}" for number,name in code_name_map.items())
    raise argparse.ArgumentTypeError(f"未知C程序{value}；可选值为{choices}")

def cli():
    parser=argparse.ArgumentParser(description="构建并启动ASZ验证用C程序")
    parser.add_argument("code",type=resolve_code_name,help="程序编号2到8，或完整程序名")
    parser.add_argument("--skip-build",action="store_true",help="使用已有安装，不重新构建")
    parser.add_argument("--silent-build",action="store_true",help="隐藏成功的构建输出")
    arguments=parser.parse_args()
    if not arguments.skip_build:
        run_command(["cmake","-S",project_root/"c_codes","-B",project_root/"build",f"-DCODE_NAME={arguments.code}",f"-DCMAKE_INSTALL_PREFIX={project_root/'install'}"],arguments.silent_build)
        run_command(["cmake","--build",project_root/"build","--parallel","4"],arguments.silent_build)
        run_command(["cmake","--install",project_root/"build"],arguments.silent_build)
    run_command([project_root/"install/bin"/arguments.code])

if __name__=="__main__":
    cli()
