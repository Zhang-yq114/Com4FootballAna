import pandas as pd
import os
from typing import List


def summarize_team_pass_players(output_file_path, sheet_idx, cut_output_dir):
    """按Excel格式分类接球记录，生成带sheet索引的文件名"""
    # 数据读取
    if not os.path.exists(output_file_path):
        raise FileNotFoundError(f"数据文件不存在：{output_file_path}")

    print("\n5. 传球总结")
    df = pd.read_excel(output_file_path)
    total_rows = len(df)
    print(f"5.1 传球总结开始：读取到{total_rows}行数据")

    # 识别控球行
    possession_code_pattern = r"(.+?)\s*-\s*Possessions"
    df['是否控球标识行'] = (df['text'] == 'Possessions') & (df['code'].str.match(possession_code_pattern, na=False))
    df['当前控球队伍'] = df['code'].str.extract(possession_code_pattern)[0].str.strip()

    # 打印控球标识行统计
    possession_flag_rows = df[df['是否控球标识行']]
    print(f"   - 识别到{len(possession_flag_rows)}个控球标识行")

    # 识别队伍（去重+过滤空值）
    unique_teams = df['当前控球队伍'].dropna().unique().tolist()
    print(f"   - 识别到的球队数量：{len(unique_teams)}支")
    if unique_teams:
        print(f"   - 球队名单：{', '.join(unique_teams)}")
    else:
        raise ValueError("未从数据中识别到任何球队的控球记录！请检查映射文件和原始数据")

    # 标记球员所属队伍
    df['球员所属队伍'] = None
    current_team = None

    for idx, row in df.iterrows():
        if row['是否控球标识行']:
            current_team = row['当前控球队伍']
        elif current_team is not None:
            # 识别有效球员行
            is_player_row = (pd.isna(row['text']) and
                             pd.notna(row['code']) and
                             '-' in str(row['code']) and
                             'Possessions' not in str(row['code']))
            if is_player_row:
                df.loc[idx, '球员所属队伍'] = current_team

    # 有效球员记录统计
    valid_player_records = df[df['球员所属队伍'].notna()].copy()
    print(f"   - 有效球员传球记录数：{len(valid_player_records)}条")

    # 按队伍拆分并生成Excel
    os.makedirs(cut_output_dir, exist_ok=True)
    print(f"   - 输出文件夹：{cut_output_dir}")

    for team in unique_teams:
        team_records = valid_player_records[valid_player_records['球员所属队伍'] == team]
        print(f"\n   ** {team}：")
        print(f"      - 接球记录数：{len(team_records)}条")

        if len(team_records) == 0:
            print(f"      - 警告：{team}无有效接球记录，跳过生成文件")
            continue

        # 生成球队Excel文件
        output_df = pd.DataFrame({
            "start": team_records['start'].values,
            "end": team_records['end'].values,
            "接球球员": team_records['code'].str.strip().values,
            "所属队伍": team
        })

        output_filename = f"{team}_sheet{sheet_idx}.xlsx"
        output_path = os.path.join(cut_output_dir, output_filename)

        output_df.to_excel(output_path, index=False)
        unique_players = output_df["接球球员"].unique()
        print(f"      - 参与球员数：{len(unique_players)}人")
        print(f"      - 文件生成成功：{output_path}")

    print(f"\n5.2 传球总结完成！共生成{len(unique_teams)}个球队的传球记录文件")


def summarize_combined_matches(input_dir: str, output_dir: str, team_name: str) -> None:
    """汇总多场比赛的传球数据（从CutOutput到GameSum）"""
    print("1. 开始汇总多场比赛数据...")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 收集所有相关Excel文件
    excel_files = [f for f in os.listdir(input_dir) if f.endswith(".xlsx") and team_name in f]
    if not excel_files:
        raise ValueError(f"在{input_dir}中未找到包含{team_name}的Excel文件")

    # 按球队分组汇总
    team_data = {}
    for file_idx, file_name in enumerate(excel_files, 1):
        file_path = os.path.join(input_dir, file_name)
        try:
            df = pd.read_excel(file_path)
            if "所属队伍" not in df.columns or "接球球员" not in df.columns:
                print(f"   跳过无效文件{file_name}：缺少必要列")
                continue

            team = df["所属队伍"].iloc[0] if not df.empty else "Unknown"
            if team not in team_data:
                team_data[team] = []
            team_data[team].append(df)
            print(f"   已读取 {file_idx}/{len(excel_files)}：{file_name}")
        except Exception as e:
            print(f"   读取文件{file_name}失败：{str(e)}，已跳过")

    # 合并并保存每个球队的汇总数据
    for team, dfs in team_data.items():
        combined_df = pd.concat(dfs, ignore_index=True)
        output_filename = f"{team}_combined.xlsx"
        output_path = os.path.join(output_dir, output_filename)
        combined_df.to_excel(output_path, index=False)
        print(f"   已生成{team}汇总数据：{output_path}（共{len(combined_df)}条记录）")