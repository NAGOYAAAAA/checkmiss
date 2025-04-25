import sys
import subprocess
import importlib
from pathlib import Path


def check_version(lib_name):
    package_to_module = {
        'python-dateutil': 'dateutil',
        'pandas': 'pandas',
        'chardet': 'chardet',
        'tqdm': 'tqdm',
        'requests': 'requests'
    }
    module_name = package_to_module.get(lib_name, lib_name)
    try:
        module = importlib.import_module(module_name)
        return module.__version__
    except ModuleNotFoundError:
        return None


def install_from_source(lib, source):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-i", source, lib],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )


def install_libraries(libs):
    sources = [
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.nankai.edu.cn/pypi/web/simple",
        "https://mirrors.aliyun.com/pypi/simple/"
    ]

    if 'tqdm' not in libs:
        libs = ['tqdm'] + libs

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"""===============================================
[系统信息] Python 版本：{python_version}
===============================================""")
    print("[依赖检查] 开始检测所需库...\n")

    successful_source = None
    if check_version('tqdm') is None:
        for source in sources:
            print(f"[尝试安装tqdm] 当前源：{source}")
            try:
                install_from_source('tqdm', source)
                successful_source = source
                print("[安装成功] tqdm已安装")
                break
            except subprocess.CalledProcessError as e:
                print(f"[安装失败] {e.stdout}")
        else:
            print("[致命错误] 所有源均无法安装tqdm，请手动安装后重启程序")
            input("按任意键退出...")
            sys.exit(1)

    # 锁定 urllib3 版本为 1.x 系列
    if 'requests' in libs:
        libs.append('urllib3<2.0')

    installed = {lib: check_version(lib) for lib in libs}
    missing = [lib for lib in libs if installed[lib] is None]

    if not missing:
        print("[依赖状态] 所有库已安装：")
        key_dependencies = ['pandas', 'python-dateutil', 'chardet', 'requests']
        for lib in key_dependencies:
            print(f" - {lib}: {installed[lib]}")
        return True

    print(f"[需要安装] 以下库未找到：{', '.join(missing)}")
    confirm = input("是否继续安装？(y/n): ").strip().lower()
    if confirm != 'y':
        print("[用户取消] 安装已取消，程序退出")
        return False

    print("\n[开始安装] 自动切换镜像源尝试安装...")
    from tqdm import tqdm
    for lib in tqdm(missing, desc="安装进度", unit="库", dynamic_ncols=True):
        if successful_source:
            try:
                print(f"\n[安装{lib}] 当前源：{successful_source}")
                install_from_source(lib, successful_source)
                installed[lib] = check_version(lib)
                print(f"[安装成功] {lib} 版本：{installed[lib]}")
                continue
            except subprocess.CalledProcessError as e:
                print(f"[安装失败] {e.stdout}")
        for source in sources:
            print(f"\n[安装{lib}] 当前源：{source}")
            try:
                install_from_source(lib, source)
                successful_source = source
                installed[lib] = check_version(lib)
                print(f"[安装成功] {lib} 版本：{installed[lib]}")
                break
            except subprocess.CalledProcessError as e:
                print(f"[安装失败] {e.stdout}")
        else:
            print(f"[严重错误] {lib} 安装失败，请手动安装：pip install {lib}")
            input("按任意键退出...")
            sys.exit(1)

    print("\n[依赖状态] 安装完成：")
    key_dependencies = ['pandas', 'python-dateutil', 'chardet', 'requests']
    for lib in key_dependencies:
        print(f" - {lib}: {installed[lib]}")
    return True


if __name__ == "__main__":
    required_libs = ['pandas', 'chardet', 'python-dateutil', 'requests', 'tqdm']
    if not install_libraries(required_libs):
        input("\n[安装失败] 按任意键退出程序...")
        sys.exit(1)

    import traceback
    import re
    import pandas as pd
    import chardet
    from dateutil.parser import parse
    from tqdm import tqdm
    import os
    import datetime
    import requests

    COLUMN_MAPPING = {
        'clinic': {
            'name': '姓名',
            'id': '身份证',
            'diagnosis': '诊断',
            'visit_time': '就诊时间'
        },
        'report': {
            'name': '患者姓名',
            'id': '有效证件号',
            'disease': '疾病名称',
            'report_time': '报告卡录入时间'
        }
    }


    def clean_date(date_str):
        try:
            date_obj = parse(date_str, dayfirst=False, yearfirst=True)
            if date_obj.time() == pd.Timestamp('00:00:00').time():
                return date_obj.strftime('%Y-%m-%d')
            else:
                return date_obj.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            if not hasattr(clean_date, 'error_samples'):
                clean_date.error_samples = []
            if len(clean_date.error_samples) < 5:
                clean_date.error_samples.append(date_str)
            return pd.NaT


    def read_data(data_path):
        raw_data = b''
        try:
            with tqdm(total=os.path.getsize(data_path), desc="读取文件", unit='B') as pbar:
                with open(data_path, 'rb') as f:
                    chunk = f.read(1024 * 1024)
                    while chunk:
                        raw_data += chunk
                        pbar.update(len(chunk))
                        chunk = f.read(1024 * 1024)
            result = chardet.detect(raw_data)
            if result['encoding'] in ['GB2312', 'GB18030']:
                encoding = 'GBK'
            else:
                encoding = result['encoding'] or 'GBK'
            if encoding == 'UTF-8-SIG':
                encoding = 'utf-8'
            data = pd.read_csv(data_path, sep=',', encoding=encoding)
        except Exception as e:
            for enc in ['GBK', 'GB18030', 'utf-8']:
                try:
                    data = pd.read_csv(data_path, sep=',', encoding=enc)
                    print(f"成功使用{enc}编码读取文件")
                    break
                except:
                    continue

        data.columns = data.columns.str.strip()
        for col in data.columns:
            if data[col].dtype != 'object':
                data[col] = data[col].astype(str)
        data.fillna("无", inplace=True)
        for time_col in [COLUMN_MAPPING['clinic']['visit_time'], COLUMN_MAPPING['report']['report_time']]:
            if time_col in data.columns:
                data[time_col] = data[time_col].apply(clean_date)
                invalid_count = data[time_col].isna().sum()
                if invalid_count > 0:
                    print(f"[格式警告] {data_path.name}的{time_col}列存在{invalid_count}条无效日期，已尽力清洗，仍有无效数据。")
                    if hasattr(clean_date, 'error_samples'):
                        print(f"无法解析的日期示例：{clean_date.error_samples}")
        return data


    def select_data(data, output_file):
        required_cols = {COLUMN_MAPPING['clinic']['visit_time'], COLUMN_MAPPING['clinic']['diagnosis']}
        missing_cols = required_cols - set(data.columns)
        if missing_cols:
            raise ValueError(
                f"缺少关键列：{missing_cols}\n"
                f"当前文件包含的列：{list(data.columns)}\n"
                "请检查文件是否符合格式要求：\n"
                "1. 使用正确的CSV格式\n"
                "2. 列名包含中文标点符号\n"
                "3. 文件编码为UTF-8或GBK"
            )

        print(f"原始数据：{len(data)}条，开始清洗诊断列...")
        data[COLUMN_MAPPING['clinic']['diagnosis']] = data[COLUMN_MAPPING['clinic']['diagnosis']].astype(
            str).str.replace(r'\s+', '', regex=True)
        print("✅ 诊断列空格清理完成")
        inf_pattern = re.compile(r"""
            新冠|新型冠状|鼠疫|霍乱|病毒性肝炎|乙肝|丙肝|丁肝|戊肝|脊灰|脊髓灰质炎|禽流感|麻疹|出血热|狂犬病|脑炎|登革热|炭疽|痢疾|菌痢|志贺氏菌|结核|乙型|甲型|丙型|传染性|伤寒|流脑|流行性脑脊髓炎|百日咳|白喉|新破|新生儿破伤风|猩红热|猩 红 热|布鲁氏菌|布病|淋病|梅毒|钩体病|钩端螺旋体病|血吸虫病|疟疾|AIDS|艾滋病|HIV|流行性感冒|流感|流腮|流行性腮腺炎|风疹|出血性结膜炎|麻风|黑热病|包虫|手足口|丝虫|感染性腹泻|轮状病毒|细菌|病毒|病毒性腹泻|细菌性腹泻|乙脑|水痘|肝炎|其它感染性腹泻病|流行性感冒
        """, re.VERBOSE | re.UNICODE)
        data_selected = data[data[COLUMN_MAPPING['clinic']['diagnosis']].str.contains(inf_pattern, na=False)]
        exclude_pattern = re.compile(r"""
            陈旧|筛查|疱疹病毒|角膜炎|荨麻疹|携带者|EB病毒|细菌性阴道|传染性单核细胞|人乳头瘤病毒|传染性软疣|开药|呼吸道.*?细菌感染|疱疹性咽峡炎|取药|拿药|鼻窦炎.*?细菌|病毒疣|乳头瘤
        """, re.VERBOSE | re.DOTALL | re.UNICODE)
        data_selected = data_selected[
            ~data_selected[COLUMN_MAPPING['clinic']['diagnosis']].str.contains(exclude_pattern, na=False)]

        print(f"🔍 筛选结果：{len(data_selected)}条有效记录")
        if COLUMN_MAPPING['clinic']['visit_time'] not in data_selected.columns:
            raise ValueError(f"筛选后数据缺少『{COLUMN_MAPPING['clinic']['visit_time']}』列")

        data_selected = data_selected.sort_values(COLUMN_MAPPING['clinic']['visit_time']).reset_index(drop=True)
        data_selected = data_selected.loc[:, ~data_selected.columns.str.contains('^Unnamed')]
        data_selected.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✅ 步骤1完成：初筛结果保存至 {output_file.resolve()}")


    def match_two_database(data_path1, data_path2):
        data1 = read_data(data_path1)
        data2 = read_data(data_path2)
        data1[COLUMN_MAPPING['clinic']['id']] = (data1[COLUMN_MAPPING['clinic']['id']].astype(str)
                                                 .str.replace(r'\.0$', '', regex=True).str.replace(
            r'[^\dA-Za-z]', '', regex=True).str.upper())
        data1[COLUMN_MAPPING['clinic']['name']] = data1[COLUMN_MAPPING['clinic']['name']].str.strip().str.replace(
            r'\s+', '', regex=True).str.upper()
        data2[COLUMN_MAPPING['report']['id']] = (data2[COLUMN_MAPPING['report']['id']].astype(str)
                                                 .str.replace(r'\.0$', '', regex=True).str.replace(
            r'[^\dA-Za-z号]', '', regex=True).str.replace(r'号', '', regex=True).str.upper())
        data2[COLUMN_MAPPING['report']['name']] = data2[COLUMN_MAPPING['report']['name']].str.strip().str.replace(
            r'\s+', '', regex=True).str.upper()
        merge_keys = {'门诊日志': [COLUMN_MAPPING['clinic']['id'], COLUMN_MAPPING['clinic']['name']],
                      '网报卡': [COLUMN_MAPPING['report']['id'], COLUMN_MAPPING['report']['name']]}
        for df, cols in merge_keys.items():
            if not all(col in data1.columns if df == '门诊日志' else col in data2.columns for col in cols):
                print(f"❌ 错误：{df} 缺少合并列 {cols}")
                return None
        data2 = data2[[COLUMN_MAPPING['report']['name'], COLUMN_MAPPING['report']['report_time'],
                       COLUMN_MAPPING['report']['disease'], COLUMN_MAPPING['report']['id']]].sort_values(
            COLUMN_MAPPING['report']['report_time']).reset_index(drop=True)
        data_match = data1.merge(data2, how='left', left_on=merge_keys['门诊日志'], right_on=merge_keys['网报卡'])
        data_match = data_match.loc[:, ~data_match.columns.str.contains('^Unnamed')]
        return data_match


    def analysis(data_match, export_txt, export_reported, export_missing, export_duplicate, time_unit):
        if {COLUMN_MAPPING['report']['report_time'], COLUMN_MAPPING['clinic']['visit_time']}.difference(
                data_match.columns):
            print("❌ 错误：合并数据缺少必要时间列")
            return

        not_reported = data_match[data_match[COLUMN_MAPPING['report']['report_time']].isna()].reset_index(drop=True)
        reported = data_match[data_match[COLUMN_MAPPING['report']['report_time']].notna()].reset_index(drop=True)
        reported[[COLUMN_MAPPING['report']['report_time'], COLUMN_MAPPING['clinic']['visit_time']]] = reported[
            [COLUMN_MAPPING['report']['report_time'], COLUMN_MAPPING['clinic']['visit_time']]].apply(pd.to_datetime,
                                                                                                     errors='coerce')
        valid_time_count = reported[
            [COLUMN_MAPPING['report']['report_time'], COLUMN_MAPPING['clinic']['visit_time']]].notna().all(axis=1).sum()
        if valid_time_count == 0:
            print("⚠️ 警告：无有效报卡数据，无法完成时间分析。请检查时间列格式是否正确。")
            return

        reported = reported.dropna(
            subset=[COLUMN_MAPPING['report']['report_time'], COLUMN_MAPPING['clinic']['visit_time']]).reset_index(
            drop=True)
        dup_cols = [COLUMN_MAPPING['clinic']['name'], COLUMN_MAPPING['clinic']['id'], COLUMN_MAPPING['report']['disease'],
                    COLUMN_MAPPING['clinic']['visit_time']]
        duplicates = data_match[data_match.duplicated(subset=dup_cols, keep=False)]
        duplicate_count = len(duplicates)
        if duplicate_count > 0:
            if '时间间隔' in duplicates.columns:
                dup_cols.append('时间间隔')
            duplicates[dup_cols].to_csv(export_duplicate, index=False, encoding='utf-8')
            print(f"⚠️ 发现{duplicate_count}条重复条目，已保存至 {export_duplicate.resolve()}")
        time_delta = reported[COLUMN_MAPPING['report']['report_time']] - reported[
            COLUMN_MAPPING['clinic']['visit_time']]
        negative_delta = (reported[COLUMN_MAPPING['report']['report_time']] < reported[
            COLUMN_MAPPING['clinic']['visit_time']]).sum()
        if negative_delta > 0:
            print(f"警告：发现{negative_delta}条记录报告时间早于就诊时间，请检查数据准确性！")
        if time_unit == 'd':
            reported['时间间隔'] = time_delta.dt.days
        else:
            reported['时间间隔'] = time_delta.dt.total_seconds() // 3600
        target_cols = [COLUMN_MAPPING['clinic']['name'], COLUMN_MAPPING['clinic']['id'],
                       COLUMN_MAPPING['clinic']['diagnosis'], COLUMN_MAPPING['clinic']['visit_time'],
                       COLUMN_MAPPING['report']['name'], COLUMN_MAPPING['report']['id'],
                       COLUMN_MAPPING['report']['disease'], COLUMN_MAPPING['report']['report_time'], '时间间隔']
        reported = reported[target_cols] if '时间间隔' in reported.columns else reported[target_cols[:-1]]
        reported.to_csv(export_reported, index=False, encoding='utf-8')
        not_reported.to_csv(export_missing, index=False, encoding='utf-8')
        timely = (reported['时间间隔'] <= (2 if time_unit == 'd' else 48)).sum()
        timely_rate = timely / len(reported) if len(reported) else 0
        report = (
            f"【报卡及时性分析】\n"
            f"总病例：{len(data_match)} | 未报卡：{len(not_reported)}({len(not_reported)/len(data_match):.2%})\n"
            f"已报卡：{len(reported)} | 及时报卡（≤{'2天' if time_unit == 'd' else '48小时'}）：{timely} | 及时率：{timely_rate:.2%}\n"
            f"已报卡文件中的重复条目：{duplicate_count} 条（姓名+身份证+疾病名称+就诊时间重复）*注意对及时率的影响"
        )
        if negative_delta > 0:
            report += f"\n警告：发现{negative_delta}条记录报告时间早于就诊时间，请检查数据准确性！"
        with open(export_txt, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 步骤2完成：分析报告保存至 {export_txt.resolve()}")


    def show_instructions():
        doc = """
        


        >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        【传染病报卡分析系统使用说明】
        version：V20250417    author：YueXiuCDC-LGY    
        功能：自动筛选传染病门诊数据并分析报卡及时性
        系统支持：Windows，MacOs，Linux
        ———————————————————————————————————————————————— 
        已测试通过Python版本：[3.7.3],[3.9.6],[3.13.3]
        ———————————————————————————————————————————————— 
        ▶ 操作步骤：
        1. 准备文件：
           - 医院门诊日志.csv（必须列：姓名、身份证、诊断、就诊时间）
           - 大疫情网报卡.csv（必须列：患者姓名、有效证件号、疾病名称、报告卡录入时间）

        2. 放置同一文件夹下：
           文件夹
           - 医院门诊日志.csv
           - 大疫情网报卡.csv
           - [本程序].py

        3. 运行程序按步骤执行
        ———————————————————————————————————————————————— 
        ▶ 注意事项：
        ✅ 查看Python版本是否为已测试通过版本
        ✅ 文件路径不能包含中文/特殊符号
        ✅ 必须使用指定文件名（区分大小写）
        ✅ 列名严格匹配：
           门诊日志：姓名、身份证、诊断、就诊时间
           网报卡：患者姓名、有效证件号、疾病名称、报告卡录入时间
        ✅ 安装依赖时自动使用清华/南开/阿里源，网络问题可手动切换源
           - 部分网络环境可能被拦截，若无法安装依赖可使用Wifi尝试

        按任意键返回主菜单...
        """
        print(doc)
        input("按任意键返回主菜单...")


    def check_update():
        try:
            current_version = "20250417"
            response = requests.get(
                "https://api.github.com/repos/username/repo/releases/latest",
                timeout=3
            )
            latest_version = response.json()['tag_name']
            if latest_version > current_version:
                print(f"发现新版本{latest_version}，请访问项目主页下载更新")
        except Exception:
            pass


    check_update()
    files = {
        '门诊日志': Path(sys.argv[0]).parent / '医院门诊日志.csv',
        '网报卡': Path(sys.argv[0]).parent / '大疫情网报卡.csv',
        '初筛结果': Path(sys.argv[0]).parent / '医院门诊日志（筛选后）.csv',
        '结果文本': Path(sys.argv[0]).parent / '结果.txt',
        '已报卡': Path(sys.argv[0]).parent / '结果(已报告卡).csv',
        '漏报卡': Path(sys.argv[0]).parent / '结果(可疑漏报卡).csv',
        '重复条目': Path(sys.argv[0]).parent / '结果（已报告卡）中重复条目.csv'
    }

    while True:
        try:
            step = input("""
                     【传染病报卡分析系统】
        version：V20250417       author：YueXiuCDC-LGY
        ***医疗机构内部使用
        ***若报错请先查看说明文档排查
        =============================================================
        仅需保证文件有效表头名称严格一致即可使用，简单易用
        - 医院门诊日志.csv
        （必须列：姓名、身份证、诊断、就诊时间）
        - 大疫情网报卡.csv
        （必须列：患者姓名、有效证件号、疾病名称、报告卡录入时间）
        =============================================================
        1. 根据字段初筛门诊日志数据
        2. 分析报卡及时性（需先完成步骤1）
        3. 查看说明文档
        4. 退出程序
        =============================================================
        输入步骤（1/2/3/4）: """).strip().lower()

            if step == '4':
                print("程序退出...")
                break

            if step == '1':
                if not files['门诊日志'].exists():
                    raise FileNotFoundError("未找到『医院门诊日志.csv』，请检查文件名")
                data = read_data(files['门诊日志'])
                select_data(data, files['初筛结果'])

            elif step == '2':
                for file in [files['初筛结果'], files['网报卡']]:
                    if not file.exists():
                        raise FileNotFoundError(f"缺少必要文件：{file.name}")
                time_unit = input("""
        输入时间精度（d=天/h=小时）: """).strip().lower()
                while time_unit not in {'d', 'h'}:
                    time_unit = input("错误：请输入 d 或 h: ").strip().lower()
                data_match = match_two_database(files['初筛结果'], files['网报卡'])
                if data_match is not None:
                    analysis(
                        data_match,
                        files['结果文本'],
                        files['已报卡'],
                        files['漏报卡'],
                        files['重复条目'],
                        time_unit
                    )

            elif step == '3':
                show_instructions()

            else:
                raise ValueError("请输入有效步骤（1/2/3/4）")

        except Exception as e:
            error_log = Path(sys.argv[0]).parent / 'error_log.txt'
            with open(error_log, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now()}\n")
                f.write(traceback.format_exc())
            print(f"错误详情已记录至：{error_log.resolve()}")
            print(f"\n{'=' * 50}")
            print(f"❌ 程序异常：{str(e)}")
            traceback.print_exc()
            print(f"{'=' * 50}")
            print("排查建议：\n1. 检查文件是否存在且列名正确\n2. 确保日期格式为YYYY-MM-DD\n3. 手动安装缺失库：pip install pandas chardet tqdm python-dateutil requests")

    if sys.platform.startswith('win'):
        input("\n按任意键退出程序...")
    