from collections import defaultdict


def compare_players(base_players, base_player_team, current_players, current_player_team, base_sheet_idx,
                    current_sheet_idx):
    """
    对比两个sheet的球员差异
    """
    # 校验索引是否相同
    if base_sheet_idx == current_sheet_idx:
        print(f"基准sheet{base_sheet_idx}与当前sheet{current_sheet_idx}索引相同，无需对比！")
        return

    # 计算核心差异
    added_players = current_players - base_players
    missing_players = base_players - current_players

    # 按球队分组统计差异
    team_diff = defaultdict(lambda: {"missing": [], "added": []})
    # 缺失球员
    for player in missing_players:
        team = base_player_team.get(player, "未知球队")
        team_diff[team]["missing"].append(player)
    # 新增球员
    for player in added_players:
        team = current_player_team.get(player, "未知球队")
        team_diff[team]["added"].append(player)

    # 格式化输出对比结果
    print("\n" + "=" * 65)
    print(f"球员对比结果（基准sheet{base_sheet_idx} vs 当前sheet{current_sheet_idx}）")
    print("=" * 65)
    print(f"基准sheet总球员数：{len(base_players)} | 当前sheet总球员数：{len(current_players)}")
    print("\n【差异详情】")

    has_diff = False
    for team in sorted(team_diff.keys()):
        missing = sorted(team_diff[team]["missing"])
        added = sorted(team_diff[team]["added"])
        if not missing and not added:
            continue

        has_diff = True
        print(f"\n{team}：")
        if missing:
            print(f"  缺失球员（原属基准sheet）：{', '.join(missing)}")
        if added:
            print(f"  新增球员（现属当前sheet）：{', '.join(added)}")

    if not has_diff:
        print("\n两个sheet的球员名单完全一致，无增减差异！")
    print("=" * 65 + "\n")