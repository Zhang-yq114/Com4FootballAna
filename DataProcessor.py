import pandas as pd
import os
import json
from collections import defaultdict


def load_and_filter_data(filename, sheet_idx, useful_test):
    """加载Excel文件并筛选有效数据"""
    df = pd.read_excel(filename, sheet_name=sheet_idx)

    # 筛选text列包含目标值的行
    col5 = df.iloc[:, 4].astype(str)
    filtered_df = df.loc[col5.isin(useful_test)].copy()

    # 构造输出数据结构
    output_df = pd.DataFrame({
        "start": filtered_df.iloc[:, 1],
        "end": filtered_df.iloc[:, 2],
        "code": filtered_df.iloc[:, 3]
    })
    output_df["text"] = col5.where(col5 != "Successful passes", None)

    # 增加第二行Possessions记录
    count = 0
    target_3 = target_4 = None
    for _, row in output_df.iterrows():
        if row["text"] == "Possessions":
            count += 1
            if count == 2:
                target_3 = row["code"]
                target_4 = row["text"]
                break
    if target_3 and target_4:
        new_row = pd.DataFrame([{"start": None, "end": None, "code": target_3, "text": target_4}])
        output_df = pd.concat([new_row, output_df], ignore_index=True)

    return output_df


def extract_possession_phases(output_df):
    """从筛选后的数据中识别控球阶段"""
    possession_phases = []
    current_team = None
    current_players = []
    current_start_idx = None

    for idx, row in output_df.iterrows():
        col3_val = str(row.iloc[2]) if len(row) > 2 else ""
        # 识别球队
        if "- Possessions" in col3_val:
            if current_team:
                # 保存上一支球队的控球阶段
                possession_phases.append({
                    "team": current_team,
                    "players": current_players.copy(),
                    "start_idx": current_start_idx,
                    "end_idx": idx - 1
                })
            # 更新当前球队信息
            current_team = col3_val.split(" - ")[0].strip()
            current_players = []
            current_start_idx = idx
        else:
            # 提取该控球阶段的球员
            if current_team and "-" in col3_val and any(c.isdigit() for c in col3_val.split("-")[0].strip()):
                current_players.append(col3_val.strip())

    # 保存最后一支球队的控球阶段
    if current_team:
        possession_phases.append({
            "team": current_team,
            "players": current_players.copy(),
            "start_idx": current_start_idx,
            "end_idx": len(output_df) - 1
        })

    return possession_phases


def generate_auto_mapping(possession_phases):
    """根据控球阶段生成球队-球员映射（按球员出现次数匹配球队）"""
    player_team_counts = defaultdict(lambda: defaultdict(int))
    # 统计每个球员在各球队的出现次数
    for phase in possession_phases:
        for player in phase["players"]:
            player_team_counts[player][phase["team"]] += 1

    # 球员→球队映射（按出现次数最多的球队匹配）
    player_team = {p: max(ts.items(), key=lambda x: x[1])[0] for p, ts in player_team_counts.items()}
    # 球队→球员映射
    team_players = defaultdict(list)
    for player, team in player_team.items():
        team_players[team].append(player)

    return dict(team_players), player_team


def save_team_players_mapping(team_players, save_path):
    """将自动生成的球队-球员映射保存为JSON文件"""
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(team_players, f, ensure_ascii=False, indent=2)


def load_team_players_mapping(load_path):
    """读取手动调整后的球队-球员映射文件"""
    if not os.path.exists(load_path):
        raise FileNotFoundError(f"手动映射文件不存在：{load_path}")
    with open(load_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sheet_player_info(filename, sheet_idx, useful_test):
    """获取指定sheet的球员集合和球员→球队映射"""
    output_df = load_and_filter_data(filename, sheet_idx, useful_test)
    possession_phases = extract_possession_phases(output_df)
    _, player_team = generate_auto_mapping(possession_phases)
    return set(player_team.keys()), player_team


def merge_consecutive_players(cleaned_df):
    """上下行球员code相同 → 合并为一行，start取上一行，end取下一行"""
    if cleaned_df.empty:
        return cleaned_df

    # 复制原数据，避免修改原始引用
    merged_df = cleaned_df.copy().reset_index(drop=True)
    if len(merged_df) < 2:
        return merged_df

    # 标记需要保留的行索引
    keep_indices = [True] * len(merged_df)
    # 遍历数据，从后往前检查连续重复
    for i in range(len(merged_df) - 1, 0, -1):
        current_row = merged_df.iloc[i]
        prev_row = merged_df.iloc[i - 1]

        # 仅处理球员行
        is_current_player = pd.isna(current_row["text"]) and "-" in str(
            current_row["code"]) and "Possessions" not in str(current_row["code"])
        is_prev_player = pd.isna(prev_row["text"]) and "-" in str(prev_row["code"]) and "Possessions" not in str(
            prev_row["code"])

        if is_current_player and is_prev_player and current_row["code"].strip() == prev_row["code"].strip():
            merged_df.loc[i - 1, "end"] = current_row["end"]
            keep_indices[i] = False

    merged_df = merged_df[keep_indices].reset_index(drop=True)
    return merged_df


def clean_data(output_df, possession_phases, custom_team_players, filename, sheet_idx, output_dir):
    """根据「自动生成+手动调整」的映射清理数据 + 新增连续重复球员合并"""
    # 验证映射格式
    if not isinstance(custom_team_players, dict) or len(custom_team_players) == 0:
        raise ValueError("球队-球员映射必须是有效的字典（格式：{球队名: [球员1, 球员2,...]}）")

    # 转换映射为：球员→球队
    player_correct_team = {}
    for team, players in custom_team_players.items():
        for player in players:
            player_correct_team[player.strip()] = team

    # 标记有效行
    rows_to_keep = [False] * len(output_df)
    for phase in possession_phases:
        valid_players_count = 0
        valid_player_rows = []
        # 遍历该控球阶段的所有行
        for idx in range(phase["start_idx"], phase["end_idx"] + 1):
            if idx >= len(output_df):
                continue
            row = output_df.iloc[idx]
            col3_val = str(row.iloc[2]) if len(row) > 2 else ""
            # 筛选有效球员记录
            if "-" in col3_val and any(
                    c.isdigit() for c in col3_val.split("-")[0].strip()) and "Possessions" not in col3_val:
                player_original = col3_val.strip()
                # 只有球员属于当前控球球队，才保留
                if player_correct_team.get(player_original) == phase["team"]:
                    rows_to_keep[idx] = True
                    valid_players_count += 1
                    valid_player_rows.append(idx)
        # 控球阶段至少2名有效球员才保留该阶段标记行
        if valid_players_count >= 2:
            rows_to_keep[phase["start_idx"]] = True
        else:
            for idx in valid_player_rows:
                rows_to_keep[idx] = False

    # 应用筛选条件
    cleaned_df = output_df[rows_to_keep].copy().reset_index(drop=True)
    print(f"数据清理完成（筛选有效行）：原始{len(output_df)}行 → 清理后{len(cleaned_df)}行")

    # 合并连续重复的球员记录
    cleaned_df = merge_consecutive_players(cleaned_df)

    # 保存清理后的数据
    os.makedirs(output_dir, exist_ok=True)
    file_basename = os.path.basename(filename)
    file_name_without_ext = os.path.splitext(file_basename)[0]
    output_filename = f"{file_name_without_ext}_sheet{sheet_idx}.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    cleaned_df.to_excel(output_path, index=False)

    print(f"最终文件路径：{output_path}")
    print(f"最终数据统计：筛选后{len(output_df[rows_to_keep])}行 → 合并后{len(cleaned_df)}行")

    return output_path