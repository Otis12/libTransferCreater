import json
import os
from openai import OpenAI
import threading
import concurrent.futures
import re
import time
from typing import List, Dict, Any
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

# 文件夹路径
folder_path = "workdir"
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# OpenAI 配置
EVAL_MODEL_TEMPERATURE = 0.5
EVAL_MODEL_MAX_TOKENS = 4000
# openai_base_url = "https://ark.cn-beijing.volces.com/api/v3"
openai_base_url = "https://4.0.wokaai.com/v1"
openai_api_key = "sk-0cgPmOv5uCArGgjtjB5TDOa2TTZTbqI0K1ujqCMdh4tOA5ET"
# openai_model = "ep-20250220194756-f4prd" # v3
openai_model = "deepseek-v3" # v3
# openai_model = "ep-20250220194257-84nxs"

# 初始化 OpenAI 客户端
client = OpenAI(
    base_url=openai_base_url,
    api_key=openai_api_key
)

# 系统提示
system_prompt = """
你是一个静态分析专家，尤其是污点分析方向。你的任务是根据给定的函数签名和函数体内容，分析其中的数据流向，生成多个 JSON 对象，该对象是污点分析中transfer的规则，该对象包含三个字段： method、from、to。
其中， method 字段表示 Java 代码中的函数签名，from 字段表示在该方法中数据流向的起点，to 字段表示在该方法中数据流向的终点。

注意：在生成 method 字段时，必须严格遵守以下格式要求：
1. 方法签名中的参数类型后不要包含参数名，例如：
   - 正确格式：<org.apache.commons.lang3.CharSet: boolean contains(char)>
   - 错误格式：<org.apache.commons.lang3.CharSet: boolean contains(char ch)>
2. 如果方法有多个参数，参数之间用逗号分隔，例如：
   - 正确格式：<java.lang.String: void getChars(int,int,char[],int)>
   - 错误格式：<java.lang.String: void getChars(int srcBegin,int srcEnd,char[] dst,int dstBegin)>

你需要仔细分析函数体内容来确定数据流向。例如：
1. 如果函数将参数赋值给类的成员变量，则 from 应该是参数位置，to 应该是 "base"
2. 如果函数返回某个参数或成员变量，则 from 应该是参数位置或 "base"，to 应该是 "result"
3. 如果函数将某个参数赋值给另一个参数，则 from 和 to 应该是相应的参数位置

以下情况不需要生成 transfer rules：
1. 函数涉及模板/泛型（如 <T>, <E> 等）
2. 函数有缺省参数
3. 参数类型在运行时才能确定
4. 函数体为空或只包含注释
5. 函数不涉及任何数据流向

示例1：
函数签名：<java.lang.String: void getChars(int,int,char[],int)>
函数体：
    public void getChars(int srcBegin, int srcEnd, char[] dst, int dstBegin) {
        if (srcBegin < 0) {
            throw new StringIndexOutOfBoundsException(srcBegin);
        }
        if (srcEnd > value.length) {
            throw new StringIndexOutOfBoundsException(srcEnd);
        }
        if (srcBegin > srcEnd) {
            throw new StringIndexOutOfBoundsException(srcEnd - srcBegin);
        }
        System.arraycopy(value, srcBegin, dst, dstBegin, srcEnd - srcBegin);
    }
分析：这个函数将字符串的内容复制到目标字符数组中，数据从字符串本身流向目标数组。因此应该生成：
[
    {
        "method": "<java.lang.String: void getChars(int,int,char[],int)>",
        "from": "base",
        "to": "2"
    }
]

示例2：
函数签名：<java.util.ArrayList: boolean add(java.lang.Object)>
函数体：
    public boolean add(E e) {
        ensureCapacityInternal(size + 1);
        elementData[size++] = e;
        return true;
    }
分析：这个函数涉及泛型参数 E，不需要生成 transfer rules。

当你认为该函数不会对数据流向产生影响时或者函数中涉及到了模板和泛型，可以不生成 JSON 对象。
不要再返回值中添加```json```等信息,不过需要严格按照 JSON 对象格式来生成返回值。不要在回答中写任何的说明和解释，仅仅返回json对象即可！。

注意：生成的结果中，例如 {  
    "method": "<java.lang.String: void getChars(int,int,char[],int)>", 
    "from": base, 
    "to": 2 
    },
中 java.lang.String: void getChars(int,int,char[],int) 冒号后有一个空格，请严格遵守这个格式。

注意：函数签名后有时会有static，表示该方法是静态方法，其from和to的值均不可能是base。
并且如果遇到static的方法，但函数不接收任何参数，就不用生成transfer rules。

其中base表示本身，result表示返回值,0表示参数位置。
如果遇到数组或者可变参数的情况下，则在参数位置后加上[*]即可。
"""

# 全局字典，用于存储已经处理过的函数签名及其 transfer rules
global_rules = {}
global_rules_lock = threading.Lock()

def read_method_details(file_path: str) -> List[Dict[str, Any]]:
    """读取方法详情文件"""
    methods = []
    current_method = {}
    current_content = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('<') and line.endswith('>'):
            # 保存前一个方法
            if current_method:
                current_method['content'] = '\n'.join(current_content)
                methods.append(current_method)
                current_method = {}
                current_content = []
            
            # 解析新方法
            method_info = line[1:-1]  # 去掉 < >
            parts = method_info.split(': ')
            if len(parts) == 2:
                class_name, method_sig = parts
                current_method['class_name'] = class_name
                current_method['method_signature'] = method_sig
        elif line.startswith('Package:'):
            current_method['package'] = line.replace('Package:', '').strip()
        elif line.startswith('Is Public API:'):
            current_method['is_public_api'] = line.replace('Is Public API:', '').strip() == 'true'
        elif line.startswith('Content:'):
            current_content = []
        elif line == '---':
            if current_method:
                current_method['content'] = '\n'.join(current_content)
                methods.append(current_method)
                current_method = {}
                current_content = []
        elif current_method:
            current_content.append(line)
    
    # 处理最后一个方法
    if current_method:
        current_method['content'] = '\n'.join(current_content)
        methods.append(current_method)
    
    return methods

def load_existing_rules(output_file: str):
    """
    加载已存在的 transfer rules 文件。
    """
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_rules(output_file: str, rules: dict):
    """
    将 transfer rules 保存到 JSON 文件。
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=4, ensure_ascii=False)

def extract_json_from_text(text: str) -> list:
    """
    从文本中提取JSON数组。
    尝试多种方式提取：
    1. 直接解析整个文本
    2. 查找并提取 [...] 中的内容
    3. 查找并提取 {...} 中的内容并组合成数组
    """
    print("\n[DEBUG] 开始提取JSON...")
    try:
        # 尝试直接解析整个文本
        print("[DEBUG] 尝试直接解析整个文本...")
        return json.loads(text)
    except json.JSONDecodeError:
        print("[DEBUG] 直接解析失败，尝试提取数组...")
        try:
            # 尝试提取 [...] 中的内容
            array_match = re.search(r'\[(.*)\]', text, re.DOTALL)
            if array_match:
                print("[DEBUG] 找到数组，尝试解析...")
                return json.loads(array_match.group(0))
        except Exception as e:
            print(f"[DEBUG] 数组提取失败: {str(e)}")
            try:
                # 尝试提取所有 {...} 中的内容并组合成数组
                print("[DEBUG] 尝试提取独立对象...")
                object_matches = re.finditer(r'\{[^{}]*\}', text)
                objects = []
                for match in object_matches:
                    try:
                        obj = json.loads(match.group(0))
                        objects.append(obj)
                    except Exception as e:
                        print(f"[DEBUG] 对象解析失败: {str(e)}")
                        continue
                if objects:
                    print(f"[DEBUG] 成功提取 {len(objects)} 个对象")
                    return objects
            except Exception as e:
                print(f"[DEBUG] 对象提取失败: {str(e)}")
                pass
    print("[DEBUG] 所有提取方法都失败")
    return []

def process_method(method: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个方法，生成转换规则"""
    # 构建完整的类名（包含包名）
    full_class_name = f"{method['package']}.{method['class_name']}" if method.get('package') else method['class_name']
    
    # 构建用户提示词
    user_prompt = f"""函数签名：<{full_class_name}: {method['method_signature']}>
函数体：
{method['content']}"""

    print(f"\n[DEBUG] 处理方法: {full_class_name}: {method['method_signature']}")
    print(f"[DEBUG] 用户提示词:\n{user_prompt}")

    # 调用OpenAI API
    try:
        print("[DEBUG] 开始调用API...")
        start_time = time.time()
        response = client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=EVAL_MODEL_MAX_TOKENS,
            temperature=EVAL_MODEL_TEMPERATURE,
        )
        end_time = time.time()
        print(f"[DEBUG] API调用完成，耗时: {end_time - start_time:.2f}秒")
        
        # 提取JSON内容
        content = response.choices[0].message.content
        print(f"[DEBUG] 大模型原始输出:\n{content}")
        
        # 找到JSON开始和结束的位置
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != 0:
            json_str = content[start:end]
            try:
                rules = json.loads(json_str)
                # 确保返回的规则中使用全限定名
                for rule in rules:
                    if 'method' in rule:
                        method_parts = rule['method'].split(': ')
                        if len(method_parts) == 2:
                            class_name = method_parts[0].strip('<>')
                            method_sig = method_parts[1]
                            rule['method'] = f"<{full_class_name}: {method_sig}>"
                print(f"[DEBUG] 成功解析JSON，规则数量: {len(rules)}")
                return rules
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON解析失败: {str(e)}")
                return None
        else:
            print("[DEBUG] 未找到JSON数组")
            return None
    except Exception as e:
        print(f"[DEBUG] API调用异常: {str(e)}")
        return None

def process_file(file_path: str) -> None:
    """处理单个文件"""
    print(f"\n[DEBUG] 开始处理文件: {file_path}")
    
    # 读取方法详情
    methods = read_method_details(file_path)
    if not methods:
        print(f"[DEBUG] 文件中未找到方法")
        return
    
    print(f"[DEBUG] 找到 {len(methods)} 个方法")
    
    # 处理每个方法
    transfer_rules = []
    for i, method in enumerate(methods, 1):
        if method.get('is_public_api', False):
            print(f"\n[DEBUG] 处理第 {i}/{len(methods)} 个方法")
            rules = process_method(method)
            if rules:
                transfer_rules.extend(rules)
                print(f"[DEBUG] 已添加 {len(rules)} 条规则")
    
    # 保存转换规则
    if transfer_rules:
        output_file = file_path.replace('method_details_', 'transfer_rules_').replace('.txt', '.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transfer_rules, f, indent=4, ensure_ascii=False)
        print(f"[DEBUG] 已生成转换规则文件: {output_file}，包含 {len(transfer_rules)} 条规则")
    else:
        print(f"[DEBUG] 未生成任何转换规则")

def main():
    print("开始处理 method_details 文件...\n")  # 添加立即输出
    # 获取所有 method_details_*.txt 文件
    method_files = glob.glob('method_details_*.txt')
    
    if not method_files:
        print("未找到任何 method_details_*.txt 文件！")
        return
    
    print(f"找到 {len(method_files)} 个 method_details 文件\n")
    
    # 创建线程池
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务
        futures = [executor.submit(process_file, file) for file in method_files]
        
        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"处理文件时发生错误: {str(e)}\n")
    
    print("所有文件处理完成！\n")

if __name__ == "__main__":
    main()