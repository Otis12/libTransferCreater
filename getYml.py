# # import json

# # # 输入和输出文件路径
# # input_file = 'transfer_rules.json'
# # output_file = 'output.yml'


# # # 读取 JSON 文件内容
# # with open(input_file, 'r') as f:
# #     data = json.load(f)

# # # 生成目标格式的字符串列表
# # formatted_lines = []
# # for method_name, method_data in data.items():
# #     formatted_line = f"- {{ method: \"{method_data['method']}\", from: {method_data['from']}, to: {method_data['to']} }}\n"
# #     formatted_lines.append(formatted_line)

# # # 将结果写入新的文件
# # with open(output_file, 'w') as f:
# #     f.writelines(formatted_lines)

# # print(f"结果已生成并保存到文件: {output_file}")

# import json

# # 输入 JSON 文件路径
# input_file = 'transfer_rules.json'
# # 输出文件路径
# output_file = 'output.yml'

# # 读取 JSON 文件内容
# with open(input_file, 'r') as f:
#     data = json.load(f)

# # 生成目标格式的字符串列表
# formatted_lines = []
# for method_name, method_data in data.items():
#     from_val = method_data['from']
#     to_val = method_data['to']

#     # 检查 from 和 to 的值是否是 base、result 或者数字
#     if (
#         from_val in ('base', 'result') or from_val.isdigit()
#     ) and (
#         to_val in ('base', 'result') or to_val.isdigit()
#     ):
#         formatted_line = f"- {{ method: \"{method_data['method']}\", from: {from_val}, to: {to_val} }}\n"
#         formatted_lines.append(formatted_line)

# # 将结果写入新的文件
# with open(output_file, 'w') as f:
#     f.writelines(formatted_lines)

# print(f"结果已生成并保存到文件: {output_file}")

import json
import re
import os
import glob

# 输出文件路径
output_file = 'output.yml'

# 获取所有 transfer_rules_*.json 文件
json_files = glob.glob('transfer_rules_*.json')

if not json_files:
    print("未找到任何 transfer_rules_*.json 文件！")
    exit(1)

print(f"找到 {len(json_files)} 个 transfer_rules 文件")

# 生成目标格式的字符串列表
formatted_lines = []

# 正则表达式用于提取方法签名中的参数部分
param_pattern = re.compile(r'\(([^)]*)\)')

# 处理每个 JSON 文件
for json_file in json_files:
    print(f"\n[DEBUG] 处理文件: {json_file}")
    
    # 读取 JSON 文件内容
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"[DEBUG] 文件包含 {len(data)} 条规则")
    
    # 处理每条规则
    for rule in data:
        method_signature = rule['method']
        from_val = rule['from']
        to_val = rule['to']

        # 提取方法签名中的参数部分
        param_match = param_pattern.search(method_signature)
        if param_match:
            params = param_match.group(1).split(',')
            param_count = len(params) if params[0] else 0  # 处理无参数的情况
        else:
            param_count = 0

        # 检查 from 和 to 的值是否是 base、result 或者数字
        if (
            from_val in ('base', 'result') or (str(from_val).isdigit() and int(from_val) < param_count)
        ) and (
            to_val in ('base', 'result') or (str(to_val).isdigit() and int(to_val) < param_count)
        ):
            # 确保方法签名中的尖括号数量正确
            method_signature = method_signature.replace('>>', '>')
            formatted_line = f"- {{ method: \"{method_signature}\", from: {from_val}, to: {to_val} }}\n"
            formatted_lines.append(formatted_line)
            print(f"[DEBUG] 添加规则: {method_signature}")

# 将结果写入新的文件
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(formatted_lines)

print(f"\n结果已生成并保存到文件: {output_file}")
print(f"总共处理了 {len(json_files)} 个文件，生成了 {len(formatted_lines)} 条规则")

# import json
# import re

# # 输入 JSON 文件路径
# input_file = 'transfer_rules.json'
# # 输出文件路径
# output_file = 'output.yml'

# # 读取 JSON 文件内容
# with open(input_file, 'r') as f:
#     data = json.load(f)

# # 生成目标格式的字符串列表
# formatted_lines = []

# # 正则表达式用于提取方法签名中的参数部分
# param_pattern = re.compile(r'\(([^)]*)\)')

# for method_name, method_data in data.items():
#     method_signature = method_data['method']
#     from_val = method_data['from']
#     to_val = method_data['to']

#     # 提取方法签名中的参数部分
#     param_match = param_pattern.search(method_signature)
#     if param_match:
#         params = param_match.group(1).split(',')
#         param_count = len(params) if params[0] else 0  # 处理无参数的情况
#     else:
#         param_count = 0

#     # 检查 from 和 to 的值是否是 base、result 或者数字
#     if (
#         from_val in ('base', 'result') or (from_val.isdigit() and int(from_val) < param_count)
#     ) and (
#         to_val in ('base', 'result') or (to_val.isdigit() and int(to_val) < param_count)
#     ):
#         formatted_line = f"- {{ method: \"{method_data['method']}\", from: {from_val}, to: {to_val} }}\n"
#         formatted_lines.append(formatted_line)

# # 将结果写入新的文件
# with open(output_file, 'w') as f:
#     f.writelines(formatted_lines)

# print(f"结果已生成并保存到文件: {output_file}")

# import json
# import re

# # 输入 JSON 文件路径
# input_file = 'transfer_rules.json'
# # 输出文件路径
# output_file = 'output.yml'

# # 读取 JSON 文件内容
# with open(input_file, 'r') as f:
#     data = json.load(f)

# # 生成目标格式的字符串列表
# formatted_lines = []

# # 正则表达式用于提取方法签名中的参数部分
# param_pattern = re.compile(r'\(([^)]*)\)')

# for method_name, method_data in data.items():
#     method_signature = method_data['method']
#     from_val = method_data['from']
#     to_val = method_data['to']

#     # 提取方法签名中的参数部分
#     param_match = param_pattern.search(method_signature)
#     if param_match:
#         params = param_match.group(1).split(',')
#         param_count = len(params) if params[0] else 0  # 处理无参数的情况
#     else:
#         param_count = 0

#     # 检查 from 和 to 的值是否是 base、result 或者数字
#     if (
#         from_val in ('base', 'result') or (from_val.isdigit() and int(from_val) < param_count)
#     ) and (
#         to_val in ('base', 'result') or (to_val.isdigit() and int(to_val) < param_count)
#     ):
#         formatted_line = f"- {{ method: \"{method_data['method']}\", from: {from_val}, to: {to_val} }}\n"
#         formatted_lines.append(formatted_line)

# # 将结果写入新的文件
# with open(output_file, 'w') as f:
#     f.writelines(formatted_lines)

# print(f"结果已生成并保存到文件: {output_file}")

