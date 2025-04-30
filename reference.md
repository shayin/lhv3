# Cursor编辑器配置文件说明

## .cursorrules 文件

`.cursorrules`文件用于定义Cursor编辑器如何处理不同类型的文件，可以为不同文件类型指定不同的编辑器功能和插件。

### 配置结构说明

```json
{
  "rules": [
    {
      "name": "规则名称",
      "glob": "文件匹配模式",
      "use": ["功能模块1", "功能模块2"]
    }
  ]
}
```

### 当前配置内容

当前`.cursorrules`文件为量化交易系统项目配置了以下规则：

1. **前端源代码**: 适用于`src/frontend`目录下的JavaScript/TypeScript/Vue文件
2. **后端Python代码**: 适用于`src/backend`目录下的Python文件
3. **数据分析脚本**: 适用于`src/analysis`目录下的Python和Jupyter Notebook文件
4. **配置文件**: 适用于项目中所有JSON/YAML/INI等配置文件
5. **数据库模型**: 适用于`src/backend/models`目录下的Python模型文件
6. **测试文件**: 适用于`tests`目录下的所有测试文件
7. **文档文件**: 适用于项目中所有Markdown文档

## .cursorignore 文件

`.cursorignore`文件用于定义Cursor编辑器应该忽略的文件和目录，类似于`.gitignore`文件。这有助于提高编辑器性能，减少不必要的文件索引和分析。

### 当前配置内容

当前`.cursorignore`文件配置了以下类别的忽略规则：

1. **依赖包和虚拟环境**: 如`node_modules/`、`venv/`、`__pycache__/`等
2. **构建输出和缓存**: 如`dist/`、`build/`等编译输出目录
3. **临时文件和日志**: 如`logs/`、各类日志文件
4. **数据文件**: 忽略可能体积较大的数据文件，如CSV、Excel、Parquet等
5. **敏感信息和配置**: 忽略包含敏感信息的文件，如`.env`、密钥文件等
6. **IDE和编辑器配置**: 忽略其他IDE的配置文件
7. **模型和训练结果**: 忽略机器学习模型和训练结果文件
8. **其他大型文件**: 忽略压缩文件等可能较大的文件

## 配置建议

1. 根据项目结构变化及时更新这些配置文件
2. 添加新的文件类型或目录时，考虑是否需要在`.cursorrules`中添加新规则
3. 对于不需要被编辑器处理的大型文件或生成文件，及时添加到`.cursorignore`中
4. 定期检查配置文件以确保其与项目结构保持一致
