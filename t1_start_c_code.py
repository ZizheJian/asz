import os,subprocess,sys

redbegin="\033[91m"
redend="\033[0m"
silent_build=False

def run_command(command,silent=False):
    import pty,errno
    command_list=command.split()
    if silent:
        result=subprocess.run(command_list,capture_output=True,text=True,encoding="utf-8")
        if result.returncode!=0:
            print(result.stdout)
            print(result.stderr)
            exit()
        return result.stdout
    else:
        master,slave=pty.openpty()
        proc=subprocess.Popen(command_list,stdout=slave,stderr=slave,text=True,bufsize=1)
        os.close(slave)
        lines=[]
        with os.fdopen(master) as proc_stdout:
            try:
                for line in proc_stdout:
                    print(line,end="")
                    lines.append(line)
            except OSError as e:
                if e.errno!=errno.EIO:
                    raise e
        proc.wait()
        output="".join(lines)
        if proc.returncode!=0:
            print(output)
            exit()
        return output
    
code_name_map={1:"s1_cubic_prediction",
               2:"s2_sort_curves",
               3:"s3_cubic_prediction2",
               4:"s4_sort_curves_2",
               5:"s5_compress",
               6:"s6_find_best_t2_per_eb",
               61:"s61_find_best_t12_per_eb",
               7:"s7_cubic_prediction_dim1",
               71:"s71_quintic_prediction_dim1",
               8:"s8_cubic_prediction_dim2",
               9:"s9_cubic_prediction_dim3",
               10:"s10_multi_prediction_dim12",
               11:"s11_multi_prediction_dim13",
               12:"s12_multi_prediction_dim23"}

data_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/APS_DYS"

test_num=int(sys.argv[1])
code_name=code_name_map[test_num]

os.makedirs("build",exist_ok=True)
os.chdir("build")
run_command(f"cmake -DCODE_NAME={code_name} -DCMAKE_INSTALL_PREFIX=../install ../c_codes",silent=silent_build)
run_command("make install",silent=silent_build)
os.chdir("..")
run_command(f"./install/bin/{code_name}")