import os

# ==================== 操作开关配置 ====================
# 数据操作：处理原始数据，生成单场清洗后数据和拆分数据
DATA_OPERATION_ENABLED = False
# 比赛操作：汇总多场数据（基于Data阶段生成的CutOutput）
MATCH_OPERATION_ENABLED = False
# 网络操作：绘制传球网络（基于Data或Match阶段的输出）
NETWORK_OPERATION_ENABLED = True

# ==================== 数据操作配置（DATA_OPERATION_ENABLED=True时生效） ====================
# 原始数据输入
DATA_INPUT = {
    "FILENAME": "./InputData/Port24.xlsx",
    "CURRENT_SHEET": 1,
    "USEFUL_TEST": ["Successful passes", "Possessions"]
}

# 球队映射配置
TEAM_MAPPING = {
    "AUTO_GENERATE": True,
    "MANUAL_PATH": "player_name/team_players_mapping.json",
    "OVERWRITE_AUTO": False,  # 首次生成设True，修改后设False
    "CUSTOM_PLAYERS": {
        # 'Zhejiang': [
        #     '7 - D. Owusu-Sekyere', '36 - Lucas Possignolo'
        # ],
        # 'Shanghai Port': [
        #     '4 - Wang Shenchao', '16 - Xu Xin'
        # ]
    }
}

# 数据输出路径
DATA_OUTPUT = {
    "OUTPUT_DIR": "./OutputData",  # 清洗后完整数据
    "CUT_DIR": "./CutOutput"  # 按球队拆分数据
}

# 跨sheet对比配置
DATA_COMPARE = {
    "ENABLE": False,
    "BASE_SHEET": 0  # 对比的基准sheet索引
}

# ==================== 比赛操作配置（MATCH_OPERATION_ENABLED=True时生效） ====================
MATCH_SUMMARY = {
    "TEAM_NAME": "Shanghai Port",
    "INPUT_DIR": "./CutOutput",  # 从Data阶段的拆分数据读取
    "OUTPUT_DIR": "GameSum/Port24_sum"  # 汇总后的数据保存目录
}

# ==================== 网络操作配置（NETWORK_OPERATION_ENABLED=True时生效） ====================
# 网络指标计算
NETWORK_METRICS = {
    "CALCULATE": True,
    "INPUT_PATH": "CutOutput",
    "OUTPUT_PATH": "./NetworkMetrics/port24_metrics.json",
    "TARGET_METRICS": None
}

# 传球网络绘制
NETWORK_PLOT = {
    # 单场网络
    "DRAW_SINGLE": False,
    "SINGLE_INPUT_DIR": "./CutOutput",
    "SINGLE_SAVE_DIR": "./PassingNetwork",

    # 组合场次网络
    "DRAW_COMBINED": True,
    "COMBINED_INPUT_DIR": "GameSum/Port24_sum",
    "COMBINED_SAVE_DIR": "./CombinedPassingNetwork",

    # 图片保存配置
    "SAVE_IMG": True,
    "TEAM_NAME": "Port24"
}