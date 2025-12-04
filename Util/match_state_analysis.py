import pandas as pd
import os
import config
from collections import defaultdict

# 全局变量：共享数据操作的球队映射
global_team_mapping = {}


def init_team_mapping(team_players):
    """初始化状态分析的球队映射（复用数据操作的TEAM_MAPPING）"""
    global global_team_mapping
    # 从数据操作的球队-球员映射中提取球队名
    for original_team in team_players.keys():
        # 匹配配置的球队映射
        mapped_team = config.DATA_EXTENDED["TEAM_MAPPING"].get(original_team, original_team)
        global_team_mapping[original_team] = mapped_team
    print(f"🔧 状态分析初始化球队映射：{global_team_mapping}")


def parse_match_periods_and_goals(df):
    """解析时段和进球事件（基于包含所有事件的原始数据）"""
    COL_TEAM_PLAYER = 3  # 第四列
    COL_EVENT = 4  # 第五列

    # 1. 识别Start/End of period（按时间递增）
    period_markers = []
    for idx, row in df.iterrows():
        event = row["event_clean"]
        if event in ["Start of period", "End of period"]:
            period_markers.append((idx, event))

    # 分组为上下半场
    periods = []
    for i in range(0, len(period_markers) - 1, 2):
        start_idx, start_event = period_markers[i]
        end_idx, end_event = period_markers[i + 1]
        if start_event == "Start of period" and end_event == "End of period":
            period_type = "上半场" if len(periods) == 0 else "下半场"
            periods.append({
                "start_idx": start_idx,
                "end_idx": end_idx,
                "type": period_type
            })

    # 2. 识别Goals事件（按时间递增）
    goal_events = []
    team_score = defaultdict(int)
    for idx, row in df.iterrows():
        event = row["event_clean"]
        if event == "Goals":
            # 提取球队名（使用数据操作校对后的球队名）
            team_player = str(row["team_corrected"]).strip()
            team_name = None
            # 匹配全局球队映射
            for original_team, mapped_team in global_team_mapping.items():
                if original_team in team_player:
                    team_name = mapped_team
                    break
            if not team_name:
                team_name = team_player.split(" - ")[0].strip() if " - " in team_player else "未知球队"

            team_score[team_name] += 1
            goal_events.append({
                "idx": idx,
                "team": team_name,
                "score": team_score[team_name],
                "total_score": dict(team_score)
            })

    goal_events.sort(key=lambda x: x["idx"])
    return periods, goal_events


def judge_match_state(period, goal_events, all_teams):
    """判定状态（适配时间递增规则）"""
    period_start = period["start_idx"]
    period_end = period["end_idx"]
    period_type = period["type"]
    state_segments = []

    # 筛选该时段内的进球事件
    period_goals = [g for g in goal_events if period_start <= g["idx"] <= period_end]
    # 初始化：时段开始到第一个Goals前为平局
    current_score = defaultdict(int)
    last_state_start = period_start
    last_score = dict(current_score)

    # 遍历进球事件（按时间递增）
    for goal in period_goals:
        goal_idx = goal["idx"]
        # 1. 划分Goals生效前的区间：[last_state_start, goal_idx-1]
        if last_state_start <= goal_idx - 1:
            state = get_current_state(last_score, all_teams, period_goals[:period_goals.index(goal) + 1])
            state_segments.append({
                "start_idx": last_state_start,
                "end_idx": goal_idx - 1,
                "state": f"{period_type}_{state}",
                "score": dict(last_score)
            })
        # 2. 更新比分和起始点
        current_score[goal["team"]] = goal["score"]
        last_score = dict(current_score)
        last_state_start = goal_idx

    # 3. 处理最后一个区间
    final_state = get_current_state(last_score, all_teams, period_goals)
    state_segments.append({
        "start_idx": last_state_start,
        "end_idx": period_end,
        "state": f"{period_type}_{final_state}",
        "score": dict(last_score)
    })

    # 无进球 → 平局
    if not period_goals:
        state_segments = [{
            "start_idx": period_start,
            "end_idx": period_end,
            "state": f"{period_type}_平局",
            "score": dict(current_score)
        }]

    return state_segments


def get_current_state(score_dict, all_teams, goal_events_period):
    """严格按规则判定状态（包含反超逻辑）"""
    if len(all_teams) != 2:
        return "未知状态"

    team1, team2 = all_teams[0], all_teams[1]
    score1 = score_dict.get(team1, 0)
    score2 = score_dict.get(team2, 0)

    # 平局：无任何进球
    if score1 == 0 and score2 == 0:
        return "平局"
    # 僵持：有进球且比分相等
    if score1 == score2:
        return "僵持"

    # 追溯进球顺序（用于反超判定）
    goal_order = [g["team"] for g in goal_events_period if g["team"] in [team1, team2]]

    if score1 > score2:
        # 球队1领先
        if goal_order and goal_order[0] == team2 and goal_order[-1] == team1:
            return "反超"
        else:
            return "领先"
    else:
        # 球队2领先
        if goal_order and goal_order[0] == team1 and goal_order[-1] == team2:
            return "反超"
        else:
            return "领先"


def split_data_by_state(df, state_segments):
    """按状态切分数据（保留所有列）"""
    state_data = defaultdict(pd.DataFrame)
    for segment in state_segments:
        start = segment["start_idx"]
        end = segment["end_idx"]
        state = segment["state"]
        if start <= end:
            segment_df = df.iloc[start:end + 1].copy()
            segment_df["比赛状态"] = state
            segment_df["该区间比分"] = str(segment["score"])
            segment_df["时间区间行号"] = f"{start}~{end}"
            state_data[state] = pd.concat([state_data[state], segment_df], ignore_index=True)
    return state_data


def save_state_data(state_data):
    """保存状态数据"""
    output_dir = config.DATA_EXTENDED["STATE_OUTPUT_DIR"]
    os.makedirs(output_dir, exist_ok=True)
    for state, df in state_data.items():
        if not df.empty:
            safe_state = state.replace("/", "_").replace("\\", "_").replace(":", "_")
            file_path = os.path.join(output_dir, f"{safe_state}.xlsx")
            # 移除临时列，保留原始列+状态列
            df = df.drop(columns=["event_clean", "is_core_data"], errors="ignore")
            df.to_excel(file_path, index=False)
            print(f"✅ 状态数据保存：{safe_state} → {file_path}（{len(df)}行）")
        else:
            print(f"⚠️ 状态{state}无有效数据")


def run_match_state_analysis(df, team_players):
    """
    主执行函数：
    - df：包含所有事件的原始数据框（经过球队映射校对）
    - team_players：数据操作生成的球队-球员映射
    """
    print(f"\n===== 比赛状态分析（共享数据操作映射）=====")

    # 1. 初始化球队映射（复用数据操作的结果）
    init_team_mapping(team_players)

    # 2. 解析时段和进球事件
    periods, goal_events = parse_match_periods_and_goals(df)
    if not periods:
        print("❌ 未识别到上下半场时段，状态分析终止")
        return
    print(f"⏰ 识别到时段：{[p['type'] for p in periods]}")
    print(f"⚽ 识别到进球数：{len(goal_events)}个 → {[g['team'] + ':' + str(g['score']) for g in goal_events]}")

    # 3. 获取比赛球队（从映射中提取）
    all_teams = list(global_team_mapping.values())
    if len(all_teams) < 2:
        print("❌ 有效球队数不足2支，状态分析终止")
        return
    print(f"🏆 比赛球队：{all_teams}")

    # 4. 判定各时段状态
    all_state_segments = []
    for period in periods:
        state_segments = judge_match_state(period, goal_events, all_teams)
        all_state_segments.extend(state_segments)
        print(f"\n📈 {period['type']}状态划分：")
        for seg in state_segments:
            print(f"   - {seg['state']}：行{seg['start_idx']}~{seg['end_idx']} | 比分{seg['score']}")

    # 5. 按状态切分数据
    state_data = split_data_by_state(df, all_state_segments)

    # 6. 保存数据
    save_state_data(state_data)
    print(f"===== 比赛状态分析完成 =====\n")