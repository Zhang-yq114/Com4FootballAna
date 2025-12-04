from DataProcessor import (
    load_and_filter_data, extract_possession_phases,
    get_sheet_player_info, clean_data, generate_auto_mapping,
    save_team_players_mapping, load_team_players_mapping
)
from Util.sheet_comparison import compare_players
from Util.pass_summary import summarize_team_pass_players, summarize_combined_matches
from Util.draw_pass_network import draw_single_pass_network, draw_combined_pass_network
import os
import json
import config

if __name__ == "__main__":
    final_team_players = {}

    # ==================== 数据操作阶段 ====================
    if config.DATA_OPERATION_ENABLED:
        print("===== 数据操作阶段开始 =====")
        # 1. 加载并筛选数据
        output_df = load_and_filter_data(
            config.DATA_INPUT["FILENAME"],
            config.DATA_INPUT["CURRENT_SHEET"],
            config.DATA_INPUT["USEFUL_TEST"]
        )
        possession_phases = extract_possession_phases(output_df)
        print(
            f"1. 原始sheet{config.DATA_INPUT['CURRENT_SHEET']}数据筛选后共{len(output_df)}行, 共{len(possession_phases)}个控球阶段")

        # 2. 跨sheet球员对比
        if config.DATA_COMPARE["ENABLE"]:
            if config.DATA_COMPARE["BASE_SHEET"] == config.DATA_INPUT["CURRENT_SHEET"]:
                print(f"2. 基准sheet与当前sheet相同，跳过对比")
            else:
                try:
                    print(
                        f"2. 开启球员对比（sheet{config.DATA_COMPARE['BASE_SHEET']} vs sheet{config.DATA_INPUT['CURRENT_SHEET']}）")
                    base_players, base_player_team = get_sheet_player_info(
                        config.DATA_INPUT["FILENAME"],
                        config.DATA_COMPARE["BASE_SHEET"],
                        config.DATA_INPUT["USEFUL_TEST"]
                    )
                    current_players, current_player_team = get_sheet_player_info(
                        config.DATA_INPUT["FILENAME"],
                        config.DATA_INPUT["CURRENT_SHEET"],
                        config.DATA_INPUT["USEFUL_TEST"]
                    )
                    compare_players(
                        base_players=base_players,
                        base_player_team=base_player_team,
                        current_players=current_players,
                        current_player_team=current_player_team,
                        base_sheet_idx=config.DATA_COMPARE["BASE_SHEET"],
                        current_sheet_idx=config.DATA_INPUT["CURRENT_SHEET"]
                    )
                except Exception as e:
                    print(f"2. 球员对比失败：{str(e)}")
        else:
            print(f"2. 未开启球员对比（DATA_COMPARE.ENABLE=False）")

        # 3. 生成/加载球队-球员映射
        print(f"\n3. 球队-球员映射处理")
        try:
            if config.TEAM_MAPPING["AUTO_GENERATE"]:
                # 自动生成映射
                auto_team_players, auto_player_team = generate_auto_mapping(possession_phases)
                print(f"3.1 自动生成球队-球员映射：")
                for team, players in auto_team_players.items():
                    print(f"   - {team}（{len(players)}人）")

                # 确保映射目录存在
                mapping_dir = os.path.dirname(config.TEAM_MAPPING["MANUAL_PATH"])
                os.makedirs(mapping_dir, exist_ok=True)

                # 保存/加载映射文件
                if not os.path.exists(config.TEAM_MAPPING["MANUAL_PATH"]) or config.TEAM_MAPPING["OVERWRITE_AUTO"]:
                    save_team_players_mapping(auto_team_players, config.TEAM_MAPPING["MANUAL_PATH"])
                    print(f"3.2 自动映射已保存到：{config.TEAM_MAPPING['MANUAL_PATH']}")
                    print(f"   提示：编辑后请设置OVERWRITE_AUTO=False")
                    final_team_players = auto_team_players
                else:
                    final_team_players = load_team_players_mapping(config.TEAM_MAPPING["MANUAL_PATH"])
                    print(f"3.2 已加载手动调整后的映射：{config.TEAM_MAPPING['MANUAL_PATH']}")

                # 应用手动补充配置
                if config.TEAM_MAPPING["CUSTOM_PLAYERS"]:
                    final_team_players.update(config.TEAM_MAPPING["CUSTOM_PLAYERS"])
                    print(f"3.3 已应用自定义球员补充配置")
            else:
                # 不自动生成，直接使用手动配置
                if not config.TEAM_MAPPING["CUSTOM_PLAYERS"]:
                    raise ValueError("未开启自动生成映射，请填写CUSTOM_PLAYERS！")
                final_team_players = config.TEAM_MAPPING["CUSTOM_PLAYERS"]
                print(f"3.1 使用自定义配置的球队-球员映射")

            # 打印最终映射
            print(f"\n3.4 最终用于筛选的映射：")
            for team, players in final_team_players.items():
                print(f"   - {team}：{players[:3]}...（共{len(players)}人）")
        except Exception as e:
            print(f"3. 球队映射处理失败：{str(e)}")
            exit(1)

        # 4. 数据清理（生成单场有效数据）
        try:
            output_file_path = clean_data(
                output_df=output_df,
                possession_phases=possession_phases,
                custom_team_players=final_team_players,
                filename=config.DATA_INPUT["FILENAME"],
                sheet_idx=config.DATA_INPUT["CURRENT_SHEET"],
                output_dir=config.DATA_OUTPUT["OUTPUT_DIR"]
            )
            print(f"\n4. 数据清理完成：{output_file_path}")
        except Exception as e:
            print(f"4. 数据清理失败：{str(e)}")
            exit(1)

        # 5. 传球总结（按球队拆分）
        try:
            summarize_team_pass_players(
                output_file_path=output_file_path,
                sheet_idx=config.DATA_INPUT["CURRENT_SHEET"],
                cut_output_dir=config.DATA_OUTPUT["CUT_DIR"]
            )
        except Exception as e:
            print(f"5. 传球总结失败：{str(e)}")
            exit(1)
        print("===== 数据操作阶段完成 =====")

    # ==================== 比赛操作阶段 ====================
    if config.MATCH_OPERATION_ENABLED:
        print("\n===== 比赛操作阶段开始 =====")
        try:
            # 检查输入目录是否存在
            if not os.path.exists(config.MATCH_SUMMARY["INPUT_DIR"]):
                raise FileNotFoundError(f"输入目录不存在：{config.MATCH_SUMMARY['INPUT_DIR']}")

            # 汇总多场数据
            summarize_combined_matches(
                input_dir=config.MATCH_SUMMARY["INPUT_DIR"],
                output_dir=config.MATCH_SUMMARY["OUTPUT_DIR"],
                team_name=config.MATCH_SUMMARY["TEAM_NAME"]
            )
            print(f"1. 多场数据汇总完成，保存至：{config.MATCH_SUMMARY['OUTPUT_DIR']}")
        except Exception as e:
            print(f"比赛操作失败：{str(e)}")
            exit(1)
        print("===== 比赛操作阶段完成 =====")

    # ==================== 网络操作阶段 ====================
    if config.NETWORK_OPERATION_ENABLED:
        print("\n===== 网络操作阶段开始 =====")
        # 绘制单场传球网络
        if config.NETWORK_PLOT["DRAW_SINGLE"]:
            try:
                cut_output_dir = config.NETWORK_PLOT["SINGLE_INPUT_DIR"]
                if not os.path.exists(cut_output_dir):
                    print(f"1. 未找到单场数据文件夹：{cut_output_dir}，跳过单场网络绘制")
                else:
                    target_suffix = f"_sheet{config.DATA_INPUT['CURRENT_SHEET']}.xlsx" if config.DATA_OPERATION_ENABLED else ".xlsx"
                    for file_name in os.listdir(cut_output_dir):
                        if file_name.endswith(target_suffix):
                            team_name = file_name.replace(target_suffix, "")
                            file_path = os.path.join(cut_output_dir, file_name)
                            print(f"1.1 正在绘制 {team_name} 单场传球网络...")

                            draw_single_pass_network(
                                input_file_path=file_path,
                                team_name=team_name,
                                sheet_idx=config.DATA_INPUT["CURRENT_SHEET"] if config.DATA_OPERATION_ENABLED else None,
                                save_img=config.NETWORK_PLOT["SAVE_IMG"],
                                save_dir=config.NETWORK_PLOT["SINGLE_SAVE_DIR"]
                            )

                if config.NETWORK_PLOT["SAVE_IMG"] and os.path.exists(config.NETWORK_PLOT["SINGLE_SAVE_DIR"]):
                    print(f"1.2 单场传球网络图片保存目录：{config.NETWORK_PLOT['SINGLE_SAVE_DIR']}")
            except Exception as e:
                print(f"1. 单场传球网络绘制失败：{str(e)}")

        # 绘制多场合并传球网络
        if config.NETWORK_PLOT["DRAW_COMBINED"]:
            try:
                combined_data_folder = os.path.abspath(config.NETWORK_PLOT["COMBINED_INPUT_DIR"])
                if not os.path.exists(combined_data_folder):
                    print(f"2. 多场数据文件夹不存在：{combined_data_folder}")
                else:
                    excel_files = [f for f in os.listdir(combined_data_folder) if f.endswith(".xlsx")]
                    if not excel_files:
                        print(f"2. 文件夹内无Excel文件！")
                    else:
                        print(f"2.1 文件夹内共{len(excel_files)}个有效Excel文件")

                        draw_combined_pass_network(
                            data_folder=combined_data_folder,
                            team_name=config.NETWORK_PLOT["TEAM_NAME"],
                            save_img=config.NETWORK_PLOT["SAVE_IMG"],
                            save_dir=config.NETWORK_PLOT["COMBINED_SAVE_DIR"]
                        )

                if config.NETWORK_PLOT["SAVE_IMG"] and os.path.exists(config.NETWORK_PLOT["COMBINED_SAVE_DIR"]):
                    print(f"2.2 多场合并传球网络图片保存目录：{config.NETWORK_PLOT['COMBINED_SAVE_DIR']}")
            except Exception as e:
                print(f"2. 多场合并传球网络绘制失败：{str(e)}")

        # 计算网络指标
        if config.NETWORK_METRICS["CALCULATE"]:
            try:
                from network_analysis import calculate_network_metrics

                print("\n3. 开始计算网络指标...")
                metrics_result = calculate_network_metrics(
                    input_path=config.NETWORK_METRICS["INPUT_PATH"],
                    output_path=config.NETWORK_METRICS["OUTPUT_PATH"],
                    target_metrics=config.NETWORK_METRICS["TARGET_METRICS"],
                    team_name=config.NETWORK_PLOT["TEAM_NAME"]
                )
                print("3. 网络指标计算完成！")
            except Exception as e:
                print(f"3. 网络指标计算失败：{str(e)}")
        print("===== 网络操作阶段完成 =====")