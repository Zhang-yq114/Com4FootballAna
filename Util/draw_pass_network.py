import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
from typing import List


def draw_single_pass_network(
        input_file_path: str,
        team_name: str,
        sheet_idx: int = None,
        save_img: bool = False,
        save_dir: str = "./PassingNetwork",
        fig_size: tuple = (12, 10),
        node_size: int = 800,
        node_color: str = "lightblue"
) -> None:
    """绘制单场传球网络"""
    try:
        df = pd.read_excel(input_file_path)
        required_col = "接球球员"
        pass_sequence = df[required_col].dropna().tolist()

        subtitle = f"Sheet{sheet_idx}" if sheet_idx is not None else "Single Match"
        _draw_network_core(pass_sequence, team_name, subtitle, save_img, save_dir, fig_size, node_size, node_color)
    except Exception as e:
        print(f"绘制{team_name}传球网络失败：{str(e)}")


def draw_combined_pass_network(
        data_folder: str,
        team_name: str,
        save_img: bool = False,
        save_dir: str = "./CombinedPassingNetwork",
        fig_size: tuple = (14, 12),
        node_size: int = 1000,
        node_color: str = "lightcoral"
) -> None:
    """合并文件夹内所有Excel数据，绘制总传球网络"""
    try:
        print("   正在读取文件夹内所有传球数据...")
        combined_pass_sequence = []
        excel_files = [f for f in os.listdir(data_folder) if f.endswith(".xlsx")]

        for file_idx, file_name in enumerate(excel_files, 1):
            file_path = os.path.join(data_folder, file_name)
            try:
                df = pd.read_excel(file_path)
                # 检查是否有"接球球员"列
                if "接球球员" not in df.columns:
                    print(f"   × 跳过无效文件{file_name}：缺少'接球球员'列")
                    continue
                # 提取非空的接球球员，添加到合并序列
                file_pass_sequence = df["接球球员"].dropna().tolist()
                combined_pass_sequence.extend(file_pass_sequence)
                print(f"   √ 已读取 {file_idx}/{len(excel_files)}：{file_name}（{len(file_pass_sequence)}条记录）")
            except Exception as e:
                print(f"   × 读取文件{file_name}失败：{str(e)}，已跳过")

        # 校验合并后的数据
        if not combined_pass_sequence:
            print("× 未获取到有效传球数据，无法绘制总传球网络！")
            return
        print(f"   数据合并完成：共{len(combined_pass_sequence)}条传球记录")

        # 绘制总传球网络
        _draw_network_core(
            pass_sequence=combined_pass_sequence,
            team_name=team_name,
            subtitle="Combined All Matches",
            save_img=save_img,
            save_dir=save_dir,
            fig_size=fig_size,
            node_size=node_size,
            node_color=node_color
        )

        print(f"√ {team_name}总传球网络绘制完成！")
    except Exception as e:
        print(f"× 绘制{team_name}总传球网络失败：{str(e)}")


def _draw_network_core(
        pass_sequence: List[str],
        team_name: str,
        subtitle: str,
        save_img: bool,
        save_dir: str,
        fig_size: tuple,
        node_size: int,
        node_color: str
) -> None:
    """核心绘图逻辑（抽取公共部分，避免重复代码）"""
    # 构建有向加权图
    G = nx.DiGraph()
    for i in range(len(pass_sequence) - 1):
        source = pass_sequence[i].strip()
        target = pass_sequence[i + 1].strip()
        if source == target:
            continue  # 跳过自己传给自己的情况
        if G.has_edge(source, target):
            G[source][target]['weight'] += 1
        else:
            G.add_edge(source, target, weight=1)

    # 输出统计信息
    print(f"   传球网络统计：球员数{G.number_of_nodes()} | 传球关系数{G.number_of_edges()}")

    # 可视化绘制
    plt.figure(figsize=fig_size)
    # 优化布局：spring_layout调整k值避免节点重叠
    pos = nx.spring_layout(G, seed=42, k=3.0)  # k值越大，节点间距越大

    # 绘制节点、边、标签
    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_color, alpha=0.8, edgecolors="black")
    edges = G.edges()
    weights = [G[u][v]['weight'] * 0.8 for u, v in edges]  # 边宽与传球次数成正比
    nx.draw_networkx_edges(G, pos, edgelist=edges, width=weights, edge_color='gray', arrowsize=30, alpha=0.7)
    nx.draw_networkx_labels(G, pos, font_size=9, font_family='sans-serif', font_weight='bold')

    # 绘制边权重标签（传球次数）
    edge_labels = {(u, v): f"{G[u][v]['weight']}" for u, v in G.edges()}
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, font_size=8,
        label_pos=0.3, bbox=dict(boxstyle='round,pad=0.1', fc='white', alpha=0.8)
    )

    # 图表标题
    plt.title(f"{team_name} Passing Network - {subtitle}", fontsize=16, fontweight='bold', pad=20)
    plt.axis('off')
    plt.tight_layout()

    # 保存/显示
    if save_img:
        os.makedirs(save_dir, exist_ok=True)
        save_filename = f"{team_name}_{subtitle.replace(' ', '_')}_PassingNetwork.png"
        save_path = os.path.join(save_dir, save_filename)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"   传球网络已保存到：{save_path}")
    else:
        plt.show()