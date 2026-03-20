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
    
code_name_map={1:"s1_linear_interpolation",
               2:"s2_cubic_prediction",
               3:"s3_linear_coefficient_enumerating",
               4:"s4_cubic_coefficient_enumerating",
               5:"s5_cubic_prediction",
               6:"s6_cubic_prediction",
               7:"s7_calc_cov",
               8:"s8_verify_theory_correctness"}

test_num=int(sys.argv[1])
code_name=code_name_map[test_num]

os.makedirs("build",exist_ok=True)
os.chdir("build")
run_command(f"cmake -DCODE_NAME={code_name} -DCMAKE_INSTALL_PREFIX=../install ../c_codes",silent=silent_build)
run_command("make install",silent=silent_build)
os.chdir("..")
run_command(f"./install/bin/{code_name}")