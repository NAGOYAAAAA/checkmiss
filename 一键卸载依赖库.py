import subprocess

# 定义要删除的库列表
libraries = [
    'python-dateutil',
    'pandas',
    'chardet',
    'tqdm',   “tqdm”,
    'requests'
]

for library in   在 libraries:
    try:
        # 调用 pip uninstall 命令并自动确认删除
        subprocess.run(['pip', 'uninstall', library, '-y'], check=True)
        print(f"{library} 库已成功删除。")
    except subprocess.CalledProcessError as e:
        print(f"删除 {library} 库时出错: {e}")
    
