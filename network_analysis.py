import pandas as pd
import networkx as nx
import os
from typing import List, Dict, Union
import json


def _build_graph_from_sequence(pass_sequence: List[str]) -> nx.DiGraph:
    """
    从传球序列构建有向图
    """
    G = nx.DiGraph()
    for i in range(len(pass_sequence) - 1):
        source = pass_sequence[i].strip()
        target = pass_sequence[i + 1].strip()
        if source == target:
            continue
        if G.has_edge(source, target):
            G[source][target]['weight'] += 1
        else:
            G.add_edge(source, target, weight=1)
    return G


def _get_pass_sequence(input_path: str) -> List[str]:
    """
    从输入路径（文件或文件夹）提取传球序列
    """
    pass_sequence = []
    if os.path.isfile(input_path) and input_path.endswith(".xlsx"):
        # 单场数据
        df = pd.read_excel(input_path)
        if "接球球员" in df.columns:
            pass_sequence = df["接球球员"].dropna().tolist()
    elif os.path.isdir(input_path):
        # 多场数据
        excel_files = [f for f in os.listdir(input_path) if f.endswith(".xlsx")]
        for file_name in excel_files:
            file_path = os.path.join(input_path, file_name)
            try:
                df = pd.read_excel(file_path)
                if "接球球员" in df.columns:
                    file_pass = df["接球球员"].dropna().tolist()
                    pass_sequence.extend(file_pass)
            except Exception as e:
                print(f"警告：读取文件{file_name}失败 - {str(e)}")
    else:
        raise ValueError(f"输入路径无效：{input_path}（必须是Excel文件或文件夹）")
    return pass_sequence


def calculate_network_metrics(
        input_path: str,
        output_path: str = None,
        target_metrics: List[str] = None,
        team_name: str = "Unknown Team"
) -> Dict[str, Union[Dict, float]]:
    """
    计算传球网络的所有指标（支持指定输出指标）
    """
    # 提取传球序列并构建图
    pass_sequence = _get_pass_sequence(input_path)
    if not pass_sequence:
        raise ValueError("未提取到有效传球序列，无法计算指标")
    G = _build_graph_from_sequence(pass_sequence)

    # 定义所有支持的指标及计算方法
    all_metrics = {
        # 节点中心性指标
        "node_degree": lambda: dict(G.degree()),  # 度中心性
        "node_in_degree": lambda: dict(G.in_degree()),  # 入度中心性
        "node_out_degree": lambda: dict(G.out_degree()),  # 出度中心性
        "node_betweenness": lambda: nx.betweenness_centrality(G),  # 介数中心性
        "node_closeness": lambda: nx.closeness_centrality(G),  # 接近中心性
        "node_eigenvector": lambda: nx.eigenvector_centrality(G, max_iter=1000),  # 特征向量中心性
        "node_pagerank": lambda: nx.pagerank(G),  # PageRank中心性
        "node_harmonic": lambda: nx.harmonic_centrality(G),  # 调和中心性

        # 边指标
        "edge_weight": lambda: {f"{u}→{v}": G[u][v]['weight'] for u, v in G.edges()},  # 修复：元组→字符串
        "edge_betweenness": lambda: {f"{u}→{v}": val for (u, v), val in nx.edge_betweenness_centrality(G).items()},  # 修复：元组→字符串

        # 整体网络指标
        "network_density": lambda: nx.density(G),  # 网络密度
        "network_diameter": lambda: nx.diameter(G) if nx.is_strongly_connected(G) else None, # 网络直径
        "network_radius": lambda: nx.radius(G) if nx.is_strongly_connected(G) else None, # 网络半径
        "network_average_shortest_path": lambda: nx.average_shortest_path_length(G) if nx.is_strongly_connected(G) else None, # 平均最短路径
        "network_transitivity": lambda: nx.transitivity(G),  # 传递性
        "network_average_clustering": lambda: nx.average_clustering(G),  # 平均聚类系数
        "network_number_strongly_connected_components": lambda: nx.number_strongly_connected_components(G),  # 强连通分量数
        "network_number_weakly_connected_components": lambda: nx.number_weakly_connected_components(G),  # 弱连通分量数
        "network_nodes_count": lambda: G.number_of_nodes(),  # 节点总数
        "network_edges_count": lambda: G.number_of_edges(),  # 边总数
        "network_average_degree": lambda: sum(
            dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,  # 平均度
    }

    # 筛选需要计算的指标
    metrics_to_calculate = all_metrics.keys() if target_metrics is None else [m for m in target_metrics if
                                                                              m in all_metrics]
    if not metrics_to_calculate:
        raise ValueError(f"指定的指标不存在，请从以下指标中选择：{list(all_metrics.keys())}")

    # 计算指标
    results = {
        "team_name": team_name,
        "input_path": input_path,
        "metrics": {}
    }
    for metric in metrics_to_calculate:
        try:
            results["metrics"][metric] = all_metrics[metric]()
            print(f"✓ 已计算指标：{metric}")
        except Exception as e:
            results["metrics"][metric] = f"计算失败：{str(e)}"
            print(f"✗ 指标{metric}计算失败：{str(e)}")

    # 保存结果
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到：{output_path}")

    return results