import subprocess
import sys  # 新增：用于获取当前 Python 解释器路径

# 定义要删除的库列表
libraries = [
    'python-dateutil',
    'pandas',
    'chardet',
    'tqdm',
    'requests'
]

for library in libraries:
    try:
        # 使用当前 Python 解释器调用 pip（避免路径问题）
        subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', library, '-y'],
            check=True,
            text=True  # 可选：确保输出为字符串而非字节
        )
        print(f"{library} 库已成功删除。")
    except subprocess.CalledProcessError as e:
        print(f"删除 {library} 库时出错: {e}")