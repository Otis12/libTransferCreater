import subprocess
import sys
import os

def run_cmd(cmd, cwd=None):
    print(f"\n[RUN] {cmd}")
    # 使用实时输出模式
    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1  # 行缓冲
    )
    
    # 实时读取并打印输出
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    
    # 检查是否有错误
    if process.returncode != 0:
        error = process.stderr.read()
        if error:
            print(error)
        print(f"[ERROR] 命令失败: {cmd}")
        sys.exit(process.returncode)
    
    return process

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # 1. 编译 ApiAnalyzer.java
    run_cmd("javac -encoding UTF-8 ApiAnalyzer.java")

    # 2. 运行 ApiAnalyzer
    run_cmd("java ApiAnalyzer")

    # 3. 运行 Fastmaker.py
    run_cmd(f"python Fastmaker.py")

    # 4. 运行 getYml.py
    run_cmd(f"python getYml.py")

    print("\n[ALL DONE] 全流程执行完毕，output.yml 已生成。") 