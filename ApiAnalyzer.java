import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class ApiAnalyzer {
    private static class ApiMethod {
        String className;
        String methodName;
        String returnType;
        List<String> paramTypes;
        List<String> paramNames;
        String content;
        Set<String> imports;
        String packageName;
        boolean isPublicClass;
        
        public ApiMethod(String className, String methodName, String returnType, 
                        List<String> paramTypes, List<String> paramNames, 
                        String content, Set<String> imports, String packageName,
                        boolean isPublicClass) {
            this.className = className;
            this.methodName = methodName;
            this.returnType = returnType;
            this.paramTypes = paramTypes;
            this.paramNames = paramNames;
            this.content = content;
            this.imports = imports;
            this.packageName = packageName;
            this.isPublicClass = isPublicClass;
        }
        
        public boolean isPublicApi() {
            // 检查是否是公共API
            // 1. 类必须是public的
            if (!isPublicClass) {
                return false;
            }
            
            // 2. 包名不能包含internal或impl
            if (packageName != null && 
                (packageName.contains(".internal.") || 
                 packageName.contains(".impl.") ||
                 packageName.endsWith(".internal") ||
                 packageName.endsWith(".impl"))) {
                return false;
            }
            
            // 3. 方法名不能以下划线开头（通常表示内部使用）
            if (methodName.startsWith("_")) {
                return false;
            }
            
            return true;
        }
        
        @Override
        public String toString() {
            StringBuilder sb = new StringBuilder();
            sb.append("<").append(className).append(": ");
            sb.append(returnType).append(" ");
            sb.append(methodName).append("(");
            
            // 构建参数列表，包含类型和名称
            List<String> params = new ArrayList<>();
            for (int i = 0; i < paramTypes.size(); i++) {
                params.add(paramTypes.get(i) + " " + paramNames.get(i));
            }
            sb.append(String.join(", ", params));
            
            sb.append(")>\n");
            sb.append("Package: ").append(packageName).append("\n");
            sb.append("Is Public API: ").append(isPublicApi()).append("\n");
            sb.append("Content:\n").append(content).append("\n");
            sb.append("---\n");
            return sb.toString();
        }

        public String getClassName() {
            return className;
        }

        public String getMethodSignature() {
            return returnType + " " + methodName + "(" + String.join(", ", paramTypes) + ")";
        }

        public String getPackageName() {
            return packageName;
        }

        public String getContent() {
            return content;
        }
    }
    
    private static String extractPackageName(String content) {
        Pattern packagePattern = Pattern.compile("package\\s+([^;]+);");
        Matcher matcher = packagePattern.matcher(content);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return null;
    }
    
    private static Set<String> extractImports(String content) {
        Set<String> imports = new HashSet<>();
        Pattern importPattern = Pattern.compile("import\\s+([^;]+);");
        Matcher matcher = importPattern.matcher(content);
        while (matcher.find()) {
            imports.add(matcher.group(1));
        }
        return imports;
    }
    
    private static Map<String, String> buildImportMap(Set<String> imports) {
        Map<String, String> importMap = new HashMap<>();
        for (String imp : imports) {
            String simpleName = imp.substring(imp.lastIndexOf('.') + 1);
            importMap.put(simpleName, imp);
        }
        return importMap;
    }
    
    private static String toQualifiedType(String type, String packageName, Map<String, String> importMap) {
        // 处理泛型
        if (type.contains("<")) {
            int idx = type.indexOf('<');
            String base = type.substring(0, idx);
            String generic = type.substring(idx + 1, type.lastIndexOf('>'));
            String[] genericTypes = generic.split(",");
            StringBuilder sb = new StringBuilder();
            sb.append(toQualifiedType(base.trim(), packageName, importMap));
            sb.append("<");
            for (int i = 0; i < genericTypes.length; i++) {
                sb.append(toQualifiedType(genericTypes[i].trim(), packageName, importMap));
                if (i < genericTypes.length - 1) sb.append(",");
            }
            sb.append(">"
            );
            return sb.toString();
        }
        // 处理数组
        if (type.endsWith("[]")) {
            String base = type.substring(0, type.length() - 2);
            return toQualifiedType(base, packageName, importMap) + "[]";
        }
        // 已经是全限定名
        if (type.contains(".")) return type;
        // 标准库类型
        switch (type) {
            case "String": return "java.lang.String";
            case "Integer": return "java.lang.Integer";
            case "Boolean": return "java.lang.Boolean";
            case "Long": return "java.lang.Long";
            case "Double": return "java.lang.Double";
            case "Float": return "java.lang.Float";
            case "Short": return "java.lang.Short";
            case "Byte": return "java.lang.Byte";
            case "Character": return "java.lang.Character";
            case "Object": return "java.lang.Object";
            case "List": return "java.util.List";
            case "Map": return "java.util.Map";
            case "Set": return "java.util.Set";
            case "HashMap": return "java.util.HashMap";
            case "ArrayList": return "java.util.ArrayList";
            case "LinkedList": return "java.util.LinkedList";
            case "HashSet": return "java.util.HashSet";
            case "TreeSet": return "java.util.TreeSet";
            case "Queue": return "java.util.Queue";
            case "Deque": return "java.util.Deque";
            case "Collection": return "java.util.Collection";
            case "Iterator": return "java.util.Iterator";
            case "Enumeration": return "java.util.Enumeration";
            case "BigDecimal": return "java.math.BigDecimal";
            case "BigInteger": return "java.math.BigInteger";
            case "Date": return "java.util.Date";
            case "Calendar": return "java.util.Calendar";
            case "Optional": return "java.util.Optional";
        }
        // import 进来的
        if (importMap.containsKey(type)) return importMap.get(type);
        // 基本类型
        if (type.equals("int") || type.equals("long") || type.equals("float") || type.equals("double") ||
            type.equals("boolean") || type.equals("char") || type.equals("byte") || type.equals("short") || type.equals("void")) {
            return type;
        }
        // 本包下自定义类
        if (packageName != null) return packageName + "." + type;
        // 兜底
        return type;
    }
    
    private static boolean isPublicClass(String content) {
        Pattern pattern = Pattern.compile("public\\s+class\\s+\\w+");
        return pattern.matcher(content).find();
    }
    
    private static boolean hasGenericOrVarargs(String methodSignature) {
        // 检查泛型声明
        if (methodSignature.contains("<") || methodSignature.contains(">")) {
            return true;
        }
        // 检查可变参数
        if (methodSignature.contains("...")) {
            return true;
        }
        // 检查参数类型中的泛型
        if (methodSignature.matches(".*\\w+<[^>]+>.*")) {
            return true;
        }
        return false;
    }
    
    private static boolean shouldSkipMethod(String returnType, String methodName, String params) {
        // 检查方法签名中是否包含泛型
        String methodSignature = returnType + " " + methodName + "(" + params + ")";
        if (methodSignature.contains("<") || methodSignature.contains(">")) {
            return true;
        }
        
        // 检查返回值类型中的泛型
        if (returnType.contains("<") || returnType.contains(">")) {
            return true;
        }
        
        // 检查参数中的泛型
        if (params.contains("<") || params.contains(">")) {
            return true;
        }
        
        // 检查可变参数
        if (params.contains("...")) {
            return true;
        }
        
        // 检查参数类型是否不确定
        String[] paramArray = params.split(",");
        for (String param : paramArray) {
            String[] parts = param.trim().split("\\s+");
            if (parts.length >= 2) {
                String type = parts[parts.length - 2].replaceAll("final\\s+", "");
                // 如果参数类型是Object或T，跳过
                if (type.equals("Object") || type.equals("java.lang.Object") || type.equals("T")) {
                    return true;
                }
            }
        }
        
        // 检查返回值类型是否不确定
        if (returnType.equals("Object") || returnType.equals("java.lang.Object") || returnType.equals("T")) {
            return true;
        }
        
        return false;
    }
    
    private static List<ApiMethod> analyzeJavaFile(Path filePath) throws IOException {
        List<ApiMethod> methods = new ArrayList<>();
        String content = new String(Files.readAllBytes(filePath));
        String packageName = extractPackageName(content);
        Set<String> imports = extractImports(content);
        Map<String, String> importMap = buildImportMap(imports);
        boolean isPublicClass = isPublicClass(content);
        String context = filePath.getFileName().toString().replace(".java", "");
        
        // 匹配非静态的公共方法，包括泛型方法
        Pattern pattern = Pattern.compile(
            "public\\s+(?!static\\s+)(?:<[^>]+>\\s+)?([^\\s]+)\\s+([^\\s]+)\\s*\\(([^)]*)\\)\\s*\\{([^}]*)\\}"
        );
        
        Matcher matcher = pattern.matcher(content);
        while (matcher.find()) {
            String returnType = matcher.group(1).trim();
            String methodName = matcher.group(2).trim();
            String params = matcher.group(3).trim();
            String methodContent = matcher.group(4).trim();
            
            // 检查方法签名中是否包含泛型
            String methodSignature = returnType + " " + methodName + "(" + params + ")";
            
            // 检查参数类型中是否包含泛型
            boolean hasGenericParams = false;
            if (!params.isEmpty()) {
                String[] paramArray = params.split(",");
                for (String param : paramArray) {
                    String[] parts = param.trim().split("\\s+");
                    if (parts.length >= 2) {
                        String type = parts[parts.length - 2].replaceAll("final\\s+", "");
                        if (type.contains("<") || type.contains(">") || type.equals("T")) {
                            hasGenericParams = true;
                            break;
                        }
                    }
                }
            }
            
            // 如果返回值类型或参数类型包含泛型，跳过该方法
            if (returnType.contains("<") || returnType.contains(">") || 
                returnType.equals("T") || hasGenericParams) {
                continue;
            }
            
            // 检查是否需要跳过该方法
            if (shouldSkipMethod(returnType, methodName, params)) {
                continue;
            }
            
            String className = filePath.getFileName().toString().replace(".java", "");
            List<String> paramTypes = new ArrayList<>();
            List<String> paramNames = new ArrayList<>();
            
            if (!params.isEmpty()) {
                String[] paramArray = params.split(",");
                for (String param : paramArray) {
                    String[] parts = param.trim().split("\\s+");
                    if (parts.length >= 2) {
                        String type = parts[parts.length - 2].replaceAll("final\\s+", "");
                        String name = parts[parts.length - 1];
                        String qualifiedType = toQualifiedType(type, packageName, importMap);
                        paramTypes.add(qualifiedType);
                        paramNames.add(name);
                    }
                }
            }
            
            String qualifiedReturnType = toQualifiedType(returnType, packageName, importMap);
            methods.add(new ApiMethod(className, methodName, qualifiedReturnType, paramTypes, paramNames, 
                                    methodContent, imports, packageName, isPublicClass));
        }
        
        return methods;
    }
    
    public static void main(String[] args) {
        try {
            // 设置项目目录为 lib 文件夹
            Path projectDir = Paths.get("lib");
            if (!Files.exists(projectDir)) {
                System.out.println("错误：lib 文件夹不存在！");
                return;
            }

            // 遍历 lib 目录下的所有 Java 文件
            Files.walk(projectDir)
                .filter(path -> path.toString().endsWith(".java"))
                .forEach(path -> {
                    try {
                        // 分析 Java 文件
                        List<ApiMethod> methods = analyzeJavaFile(path);
                        
                        // 过滤出公共 API 方法
                        List<ApiMethod> publicMethods = methods.stream()
                            .filter(ApiMethod::isPublicApi)
                            .collect(Collectors.toList());
                        
                        if (!publicMethods.isEmpty()) {
                            // 生成输出文件名
                            String fileName = path.getFileName().toString().replace(".java", "");
                            String outputFile = "method_details_" + fileName + ".txt";
                            
                            // 写入方法详情
                            try (BufferedWriter writer = Files.newBufferedWriter(Paths.get(outputFile))) {
                                for (ApiMethod method : publicMethods) {
                                    writer.write("<" + method.getClassName() + ": " + method.getMethodSignature() + ">\n");
                                    writer.write("Package: " + method.getPackageName() + "\n");
                                    writer.write("Is Public API: " + method.isPublicApi() + "\n");
                                    writer.write("Content:\n" + method.getContent() + "\n");
                                    writer.write("---\n");
                                }
                            }
                            System.out.println("已生成文件: " + outputFile);
                        } else {
                            System.out.println("文件 " + path.getFileName() + " 中没有公共 API 方法");
                        }
                    } catch (IOException e) {
                        System.err.println("处理文件 " + path + " 时发生错误: " + e.getMessage());
                    }
                });
            
            System.out.println("分析完成！");
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
} 