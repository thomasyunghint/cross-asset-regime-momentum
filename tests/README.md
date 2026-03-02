# 单元测试说明

## 测试文件

- `test_data_loader.py`: 包含 `data_loader.py` 模块的所有单元测试

## 运行测试

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试文件

```bash
pytest tests/test_data_loader.py -v
```

### 运行特定测试类

```bash
pytest tests/test_data_loader.py::TestLoadFromFred -v
```

### 运行特定测试函数

```bash
pytest tests/test_data_loader.py::TestLoadFromFred::test_load_from_fred_success -v
```

### 显示测试覆盖率

```bash
pytest tests/ --cov=src/data_loader --cov-report=html
```

## 测试覆盖范围

### `load_from_fred` 函数
- ✅ 成功加载数据
- ✅ 使用 API key 参数
- ✅ 无 API key 时失败
- ✅ 无效符号处理
- ✅ 空数据处理
- ✅ 时区处理
- ✅ 异常处理
- ✅ FRED 不可用时的处理

### `_get_cache_path` 函数
- ✅ 创建缓存目录
- ✅ 文件名格式
- ✅ 特殊字符处理

### `load_from_cache` 函数
- ✅ 成功加载缓存
- ✅ 文件不存在处理
- ✅ 缓存过期处理
- ✅ 日期范围过滤
- ✅ 异常处理

### `save_to_cache` 函数
- ✅ 成功保存缓存
- ✅ 异常处理

### `load_from_local_csv` 函数
- ✅ 成功加载 CSV
- ✅ 不同列名格式
- ✅ 单列数据
- ✅ 文件不存在处理
- ✅ 特殊字符处理
- ✅ 异常处理

### `load_from_yfinance` 函数
- ✅ 成功加载数据
- ✅ 时区移除
- ✅ 空数据处理
- ✅ 速率限制重试
- ✅ 最大重试次数
- ✅ 非速率限制错误处理
- ✅ yfinance 不可用时的处理

### `fetch_data_with_fallback` 函数
- ✅ 缓存优先
- ✅ 缓存到 FRED 的回退
- ✅ 所有数据源的回退
- ✅ 不使用缓存
- ✅ 所有源失败
- ✅ 自定义源顺序

### `load_all_data` 函数
- ✅ 成功加载所有数据类型
- ✅ 空输入处理
- ✅ 部分失败处理
- ✅ 时区标准化
- ✅ 前向填充
- ✅ 宏观指标优先使用 FRED

## 测试特点

- **完全隔离**: 所有测试使用 mock，不依赖真实的外部 API 或网络连接
- **快速执行**: 使用 mock 避免网络延迟
- **全面覆盖**: 测试成功路径、失败路径和边界情况
- **独立运行**: 每个测试都是独立的，可以单独运行
