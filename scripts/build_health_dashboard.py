from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "001-检查结果"
OUT_DIR = ROOT / "dashboard"


def row(
    date: str,
    report: str,
    item: str,
    result: str,
    unit: str = "",
    ref: str = "",
    flag: str = "",
    category: str = "",
    source: str = "截图可见内容",
) -> dict:
    return {
        "date": date,
        "report": report,
        "category": category or report,
        "item": item,
        "result": result,
        "unit": unit,
        "reference": ref,
        "flag": flag or infer_flag(result, ref),
        "source": source,
    }


def infer_flag(result: str, ref: str) -> str:
    s = result.strip()
    if not s or s in {"-", "—"}:
        return "未判定"
    if "阳性" in s:
        return "异常"
    if "阴性" in s or "未见" in s or s == "正常":
        return "正常"
    if "↑" in s:
        return "偏高"
    if "↓" in s:
        return "偏低"

    num = parse_number(s)
    if num is None or not ref:
        return "未判定"

    ref_clean = ref.replace("－", "-").replace("–", "-").replace("—", "-").replace(" ", "")
    if ref_clean.startswith(("≤", "<=")):
        limit = parse_number(ref_clean)
        return "正常" if limit is not None and num <= limit else "偏高"
    if ref_clean.startswith(("<",)):
        limit = parse_number(ref_clean)
        return "正常" if limit is not None and num < limit else "偏高"
    if ref_clean.startswith(("≥", ">=")):
        limit = parse_number(ref_clean)
        return "正常" if limit is not None and num >= limit else "偏低"
    if ref_clean.startswith((">",)):
        limit = parse_number(ref_clean)
        return "正常" if limit is not None and num > limit else "偏低"

    m = re.search(r"(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)", ref_clean)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if num < lo:
            return "偏低"
        if num > hi:
            return "偏高"
        return "正常"
    return "未判定"


def parse_number(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(m.group(0)) if m else None


def make_records() -> list[dict]:
    records: list[dict] = []

    # 2023-10 to 2024-05 screenshots supplied in the conversation.
    records += [
        row("2023-10-16", "血型分析", "ABO血型", "O", category="基础信息", flag="正常"),
        row("2023-10-16", "血型分析", "Rh血型", "阳性(+)", category="基础信息", flag="正常"),
        row("2023-10-16", "25-羟基维生素D", "25-羟基维生素D", "17.56", "ng/mL", ">=20.00", "偏低", "营养/代谢"),
        row("2023-10-16", "糖化血红蛋白", "HbA1c", "5.55", "%", "4.00-6.00", category="糖代谢"),
        row("2023-10-16", "葡萄糖6-磷酸脱氢酶活性检测", "G6PD活性", "1.22", "kU/L", "成人:1.00-2.30", category="遗传/酶学"),
        row("2023-10-16", "乙型肝炎表面抗原测定", "HBsAg", "0.00", "IU/mL", "<0.05", category="感染筛查"),
        row("2023-10-16", "HIV Ag/Ab", "HIV抗原及抗体", "0.10", "s/co", "<1.00", category="感染筛查"),
        row("2023-10-16", "梅毒螺旋体特异抗体测定", "TPPA", "<1:80", "", "<1:80", category="感染筛查"),
        row("2023-10-16", "血浆D-二聚体测定", "D-二聚体", "384", "ng/ml FEU", "68-494", category="凝血/易栓"),
        row("2023-10-16", "血清铁蛋白", "铁蛋白", "95.00", "ng/mL", "13.00-150.00", category="营养/铁代谢"),
        row("2023-10-17", "葡萄糖6-磷酸脱氢酶活性检测", "G6PD活性", "1.22", "kU/L", "成人:1.00-2.30", category="遗传/酶学"),
        row("2023-10-19", "血红蛋白分析", "Hb A2", "2.6", "%", "2.5-3.5", category="血红蛋白"),
        row("2023-10-19", "血红蛋白分析", "Hb A", "97.4", "%", ">94.5", category="血红蛋白"),
        row("2023-10-19", "血红蛋白分析", "Hb Barts", "未见", "%", "0-0", category="血红蛋白"),
        row("2023-10-19", "血红蛋白分析", "Hb CS", "未见", "%", "0-0", category="血红蛋白"),
        row("2023-10-19", "血红蛋白分析", "血红蛋白H包涵体", "<5", "%", "<5", category="血红蛋白"),
        row("2023-11-22", "乙肝两对半定量", "乙肝核心抗体", "<0.20", "IU/mL", "<0.60", category="感染筛查"),
        row("2023-11-22", "乙肝两对半定量", "乙肝e抗体", "<0.18", "IU/mL", "<0.20", category="感染筛查"),
        row("2023-11-22", "乙肝两对半定量", "乙肝e抗原", "<0.04", "IU/mL", "<0.10", category="感染筛查"),
        row("2023-11-22", "乙肝两对半定量", "乙肝表面抗体", "<4.00", "mIU/mL", "<10.00", category="感染筛查"),
        row("2023-11-22", "乙肝两对半定量", "乙肝表面抗原", "<0.03", "IU/mL", "<0.05", category="感染筛查"),
        row("2023-11-22", "梅毒血清二项检测", "梅毒甲苯胺红不加热血清试验", "阴性", "", "阴性", category="感染筛查"),
        row("2023-11-22", "梅毒血清二项检测", "梅毒螺旋体抗体检测", "<1:80", "", "<1:80", category="感染筛查"),
        row("2023-11-23", "丙型肝炎抗体测定", "丙肝抗体", "阴性", "", "阴性", category="感染筛查"),
        row("2023-11-24", "孕早期唐氏筛查", "游离β-hCG", "22.1", "IU/L", "", category="妊娠相关"),
        row("2023-11-24", "孕早期唐氏筛查", "妊娠相关血浆蛋白A", "3927", "mIU/L", ">0.43", category="妊娠相关"),
        row("2023-11-24", "孕早期唐氏筛查", "孕周计算方法", "B超", "", "", "未判定", "妊娠相关"),
        row("2023-12-08", "孕中期唐氏综合征筛查", "甲胎蛋白", "21.45", "ng/mL", "", category="妊娠相关"),
        row("2023-12-08", "孕中期唐氏综合征筛查", "雌三醇", "0.633", "ng/mL", "0.000-52.000", category="妊娠相关"),
        row("2023-12-08", "孕中期唐氏综合征筛查", "人绒毛膜促性腺激素", "53011", "mIU/mL", "", category="妊娠相关"),
        row("2024-02-26", "肺炎支原体血清学试验", "肺炎支原体血清学试验", "<1:40", "", "<1:40", category="感染筛查"),
        row("2024-02-26", "降钙素原检测", "PCT", "<0.05", "ng/mL", "<0.05", category="炎症/感染"),
        row("2024-03-17", "血浆D-二聚体测定", "D-二聚体", "718", "ng/ml FEU", "68-494", "偏高", "凝血/易栓"),
        row("2024-03-17", "血B型钠尿肽前体", "PRO-BNP", "<10.00", "pg/mL", "<125慢性心衰排除", category="心血管"),
        row("2024-03-18", "尿干化学分析", "尿白细胞试验", "微量", "", "阴性", "异常", "尿检"),
        row("2024-03-18", "尿干化学分析", "尿比重", "1.010", "", "1.005-1.035", category="尿检"),
        row("2024-03-18", "尿干化学分析", "pH值", "7.0", "", "4.5-8.0", category="尿检"),
        row("2024-03-18", "尿干化学分析", "镜检红细胞", "未见", "/HP", "0-3", category="尿检"),
        row("2024-03-18", "尿干化学分析", "镜检白细胞", "0-2", "/HP", "0-5", category="尿检"),
        row("2024-03-18", "免疫八项", "B-ZY", "415.500", "mg/L", "105.000-395.000", "偏高", "免疫"),
        row("2024-03-18", "免疫八项", "补体C3", "1.11", "g/L", "0.90-1.80", category="免疫"),
        row("2024-03-18", "免疫八项", "补体C4", "0.156", "g/L", "0.100-0.400", category="免疫"),
        row("2024-03-18", "免疫八项", "铜蓝蛋白", "0.53", "g/L", "0.22-0.58", category="免疫"),
        row("2024-03-18", "免疫八项", "免疫球蛋白A", "1.90", "g/L", "0.70-5.00", category="免疫"),
        row("2024-03-18", "免疫八项", "免疫球蛋白G", "11.00", "g/L", "7.00-16.00", category="免疫"),
        row("2024-03-18", "免疫八项", "免疫球蛋白M", "1.84", "g/L", "0.40-2.80", category="免疫"),
        row("2024-03-18", "免疫八项", "β2-微球蛋白", "1.02", "mg/L", "1.00-2.30", category="免疫"),
        row("2024-03-18", "甲功三项", "游离三碘甲状原氨酸", "4.56", "pmol/L", "3.53-7.37", category="甲状腺"),
        row("2024-03-18", "甲功三项", "游离甲状腺素", "9.63", "pmol/L", "7.98-16.02", category="甲状腺"),
        row("2024-03-18", "甲功三项", "促甲状腺激素", "0.71", "uIU/mL", "0.56-5.91", category="甲状腺"),
        row("2024-03-18", "抗甲状腺自身抗体", "甲状腺过氧化物酶抗体", "12.30", "IU/mL", "0.00-34.00", category="甲状腺"),
        row("2024-03-18", "抗甲状腺自身抗体", "甲状腺球蛋白抗体", "12.40", "IU/mL", "0.00-115.00", category="甲状腺"),
        row("2024-03-19", "易栓症四项", "抗凝血酶", "109", "%", "80-120", category="凝血/易栓"),
        row("2024-03-19", "易栓症四项", "蛋白C活性", "110", "%", "70-130", category="凝血/易栓"),
        row("2024-03-19", "易栓症四项", "蛋白S活性", "35", "%", "55-140", "偏低", "凝血/易栓"),
        row("2024-03-19", "易栓症四项", "血管性血友病因子", "148", "%", "50-160", category="凝血/易栓"),
        row("2024-03-19", "血管炎五项", "抗肾小球基底膜抗体IgG", "阴性(-)", "", "阴性(-)", category="血管炎/自身免疫"),
        row("2024-03-19", "血管炎五项", "抗髓过氧化物酶抗体IgG", "阴性(-)", "", "阴性(-)", category="血管炎/自身免疫"),
        row("2024-03-19", "血管炎五项", "抗蛋白酶3抗体IgG", "阳性(+)", "", "阴性(-)", "异常", "血管炎/自身免疫"),
        row("2024-03-19", "血管炎五项", "cANCA效价", "1:10", "", "", "未判定", "血管炎/自身免疫"),
        row("2024-03-19", "血管炎五项", "pANCA", "阳性(+)", "", "阴性(-)", "异常", "血管炎/自身免疫"),
        row("2024-03-21", "血浆D-二聚体测定", "D-二聚体", "851", "ng/ml FEU", "68-494", "偏高", "凝血/易栓"),
        row("2024-03-21", "血管炎三项", "抗肾小球基底膜抗体", "<0.5", "U/mL", "0.00-20.00", category="血管炎/自身免疫"),
        row("2024-03-21", "血管炎三项", "髓过氧化物酶抗体", "<0.2", "mg/L", "0.00-1.50", category="血管炎/自身免疫"),
        row("2024-03-21", "血管炎三项", "蛋白酶3抗体", "186.99", "mg/L", "0.00-2.00", "偏高", "血管炎/自身免疫"),
        row("2024-03-21", "血气分析", "实际碱剩余", "-4.3", "mmol/L", "-3.2-3.5", "偏低", "血气/血常规"),
        row("2024-03-21", "血气分析", "一氧化碳血红蛋白", "1.3", "%", "0.0-0.8", "偏高", "血气/血常规"),
        row("2024-03-21", "血气分析", "标准碳酸氢根浓度", "20.9", "mmol/L", "21.3-24.8", "偏低", "血气/血常规"),
        row("2024-03-21", "血气分析", "标准碱剩余", "-4.5", "mmol/L", "-2.3-3.0", "偏低", "血气/血常规"),
        row("2024-03-21", "血气分析", "二氧化碳分压", "33.5", "mmHg", "35.0-48.0", "偏低", "血气/血常规"),
        row("2024-03-21", "血气分析", "氧分压", "110.5", "mmHg", "83.0-108.0", "偏高", "血气/血常规"),
        row("2024-03-21", "血气分析", "血红蛋白浓度", "93", "g/L", "135-175", "偏低", "血气/血常规"),
        row("2024-03-22", "狼疮样抗凝物质筛查", "LA1/LA2", "1.06", "", "0.80-1.20", category="凝血/易栓"),
        row("2024-03-22", "狼疮样抗凝物质筛查", "LA2凝固法", "36.5", "秒", "30.0-38.0", category="凝血/易栓"),
        row("2024-03-22", "狼疮样抗凝物质筛查", "LA1凝固法", "38.8", "秒", "31.0-44.0", category="凝血/易栓"),
        row("2024-03-26", "涎液化糖链抗原", "KL-6", "243", "U/mL", "≤500", category="肺部/肿瘤标志物"),
        row("2024-03-26", "肺肿瘤六项", "糖类抗原125", "23.10", "U/mL", "0.00-47.00", category="肺部/肿瘤标志物"),
        row("2024-03-26", "肺肿瘤六项", "糖类抗原153", "10.20", "U/mL", "0.00-24.00", category="肺部/肿瘤标志物"),
        row("2024-03-26", "肺肿瘤六项", "癌胚抗原", "1.59", "ng/mL", "0.00-5.00", category="肺部/肿瘤标志物"),
        row("2024-03-26", "肺肿瘤六项", "细胞角蛋白19片段", "1.80", "ng/mL", "0.00-3.30", category="肺部/肿瘤标志物"),
        row("2024-03-26", "肺肿瘤六项", "神经元特异性烯醇化酶", "8.97", "ng/mL", "0.00-16.30", category="肺部/肿瘤标志物"),
        row("2024-03-26", "肺肿瘤六项", "鳞状上皮细胞癌抗原", "0.80", "ng/mL", "0.00-1.50", category="肺部/肿瘤标志物"),
        row("2024-03-29", "自身免疫性肌炎抗体谱检测", "Jo-1/EJ/HMGCR/Ku/MDA5/Mi-2/NXP2/OJ/PL等抗体", "全部阴性(-)", "", "阴性(-)", category="血管炎/自身免疫"),
        row("2024-04-07", "血管炎三项", "抗肾小球基底膜抗体", "<0.5", "U/mL", "0.00-20.00", category="血管炎/自身免疫"),
        row("2024-04-07", "血管炎三项", "髓过氧化物酶抗体", "<0.2", "mg/L", "0.00-1.50", category="血管炎/自身免疫"),
        row("2024-04-07", "血管炎三项", "蛋白酶3抗体", "174.80", "mg/L", "0.00-2.00", "偏高", "血管炎/自身免疫"),
        row("2024-04-07", "红细胞沉降率测定", "血沉", "24", "mm/h", "0-20", "偏高", "炎症/感染"),
        row("2024-04-19", "尿干化学分析", "尿白细胞试验", "1+", "", "阴性", "异常", "尿检"),
        row("2024-04-19", "尿干化学分析", "尿比重", "1.020", "", "1.005-1.035", category="尿检"),
        row("2024-04-19", "尿干化学分析", "pH值", "6.5", "", "4.5-8.0", category="尿检"),
        row("2024-05-20", "免疫八项", "B-ZY", "392.300", "mg/L", "105.000-395.000", category="免疫"),
        row("2024-05-20", "免疫八项", "补体C3", "1.13", "g/L", "0.90-1.80", category="免疫"),
        row("2024-05-20", "免疫八项", "补体C4", "0.162", "g/L", "0.100-0.400", category="免疫"),
        row("2024-05-20", "免疫八项", "免疫球蛋白G", "9.66", "g/L", "7.00-16.00", category="免疫"),
        row("2024-05-20", "免疫八项", "免疫球蛋白M", "2.24", "g/L", "0.40-2.80", category="免疫"),
        row("2024-05-20", "血浆D-二聚体测定", "D-二聚体", "1239", "ng/ml FEU", "68-494", "偏高", "凝血/易栓"),
        row("2024-05-20", "甲胎蛋白", "甲胎蛋白", "296.00", "ng/mL", "≤7.00", "偏高", "妊娠相关/肿瘤标志物"),
        row("2024-05-20", "肝功一组", "白蛋白", "40.3", "g/L", "40.0-55.0", category="肝功能"),
        row("2024-05-20", "肝功一组", "丙氨酸氨基转移酶", "12.0", "U/L", "7.0-40.0", category="肝功能"),
        row("2024-05-20", "肝功一组", "天门冬氨酸氨基转移酶", "21.8", "U/L", "13.0-35.0", category="肝功能"),
        row("2024-05-21", "易栓症四项", "抗凝血酶III活性", "84", "%", "80-120", category="凝血/易栓"),
        row("2024-05-21", "易栓症四项", "蛋白C活性", "84", "%", "70-130", category="凝血/易栓"),
        row("2024-05-21", "易栓症四项", "蛋白S活性", "28", "%", "55-140", "偏低", "凝血/易栓"),
        row("2024-05-21", "易栓症四项", "血管性血友病因子抗原", "224", "%", "50-160", "偏高", "凝血/易栓"),
        row("2024-05-21", "血管炎三项", "抗肾小球基底膜抗体", "0.67", "U/mL", "≤20.00", category="血管炎/自身免疫"),
        row("2024-05-21", "血管炎三项", "髓过氧化物酶抗体", "<0.2", "mg/L", "≤1.50", category="血管炎/自身免疫"),
        row("2024-05-21", "血管炎三项", "蛋白酶3抗体", "158.07", "mg/L", "≤2.00", "偏高", "血管炎/自身免疫"),
        row("2024-05-21", "降钙素原检查", "PCT", "0.07", "ng/mL", "<0.05", "偏高", "炎症/感染"),
        row("2024-05-22", "狼疮样抗凝物质筛查", "LA1/LA2", "1.19", "", "0.80-1.20", category="凝血/易栓"),
        row("2024-05-22", "狼疮样抗凝物质筛查", "LA2凝固法", "32.5", "秒", "30.0-38.0", category="凝血/易栓"),
        row("2024-05-22", "狼疮样抗凝物质筛查", "LA1凝固法", "38.6", "秒", "31.0-44.0", category="凝血/易栓"),
        row("2024-05-23", "致畸四项IgM抗体检测", "巨细胞病毒IgM/单疱I、II型IgM/风疹IgM/弓形虫IgM", "全部阴性", "", "阴性", category="感染筛查"),
        row("2024-05-24", "降钙素原检查", "PCT", "<0.05", "ng/mL", "<0.05", category="炎症/感染"),
        row("2024-05-27", "血管炎五项", "抗肾小球基底膜抗体IgG", "阴性(-)", "", "阴性(-)", category="血管炎/自身免疫"),
        row("2024-05-27", "血管炎五项", "抗髓过氧化物酶抗体IgG", "阴性(-)", "", "阴性(-)", category="血管炎/自身免疫"),
        row("2024-05-27", "血管炎五项", "抗蛋白酶3抗体IgG", "阳性(+)", "", "阴性(-)", "异常", "血管炎/自身免疫"),
        row("2024-05-27", "血管炎五项", "cANCA效价", "1:10", "", "", "未判定", "血管炎/自身免疫"),
        row("2024-05-27", "血管炎五项", "pANCA", "阳性(+)", "", "阴性(-)", "异常", "血管炎/自身免疫"),
    ]

    # Direct text extraction from searchable PDFs.
    records += [
        row("2025-02-25", "胸部CT", "双肺多发小结节", "影像提示：多发小结节，拟炎性结节，建议随诊复查", "", "", "未判定", "影像"),
        row("2025-02-25", "胸部CT", "脂肪肝", "影像提示：脂肪肝", "", "", "未判定", "影像"),
        row("2025-06-26", "肝功能检验报告", "总蛋白", "72.0", "g/L", "64.0-87.0", category="肝功能", source="PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "白蛋白", "43.3", "g/L", "35.0-50.0", category="肝功能", source="PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "胆汁酸", "7.1", "umol/L", "0.1-10.0", category="肝功能", source="PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "甘胆酸", "2.6", "mg/L", "≤2.7", category="肝功能", source="PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "ALT", "62", "U/L", "1-40", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "AST", "27", "U/L", "1-37", category="肝功能", source="PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "GGT", "163", "U/L", "2-50", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "LAP", "127", "U/L", "30-70", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-06-26", "肝功能检验报告", "GLDH", "14.4", "U/L", "0.1-7.5", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-08-19", "肝酶学组合", "ALT", "48", "U/L", "1-40", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-08-19", "肝酶学组合", "AST", "29", "U/L", "1-37", category="肝功能", source="PDF文字抽取"),
        row("2025-08-19", "肝酶学组合", "GGT", "111", "U/L", "2-50", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-08-19", "肝酶学组合", "LAP", "98", "U/L", "30-70", "偏高", "肝功能", "PDF文字抽取"),
        row("2025-08-19", "肝酶学组合", "GLDH", "13.2", "U/L", "0.1-7.5", "偏高", "肝功能", "PDF文字抽取"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "红细胞(图像)", "3", "个/uL", "<10", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "白细胞(图像)", "105", "个/uL", "≤12", "偏高", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "鳞状上皮细胞(图像)", "9", "个/uL", "≤5", "偏高", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "非鳞状上皮细胞(图像)", "3", "个/uL", "≤2", "偏高", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "透明管型(图像)", "0", "个/uL", "≤2", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "病理管型(图像)", "0.0", "个/uL", "≤1.5", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "结晶(图像)", "0", "个/uL", "≤6", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "细菌(图像)", "319", "个/uL", "≤130", "偏高", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "黏液丝(图像)", "719", "个/uL", "≤264", "偏高", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "颜色", "黄色", "", "", "正常", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "浊度", "清晰", "", "", "正常", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "pH(干化学)", "5.0", "", "4.5-8.0", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "比重(干化学)", "1.027", "", "1.003-1.030", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿粒细胞酯酶(干化学)", "阳性(2+)", "", "阴性(-)", "异常", "尿检/肾脏", "最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿亚硝酸盐(干化学)", "阴性(-)", "", "阴性(-)", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿糖(干化学)", "阴性(-)", "", "阴性(-)", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿蛋白(干化学)", "阴性(-)", "", "阴性(-)", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿酮体(干化学)", "阴性(-)", "", "阴性(-)", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿胆红素(干化学)", "阴性(-)", "", "阴性(-)", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿胆原(干化学)", "阴性(-)", "", "阴性(-)", category="尿检/肾脏", source="最新截图录入"),
        row("2026-06-10", "尿沉渣定量检测,尿干化学检测", "尿隐血(干化学)", "阳性(2+)", "", "阴性(-)", "异常", "尿检/肾脏", "最新截图录入"),
    ]
    return sorted(records, key=lambda r: (r["date"], r["category"], r["item"]))


def file_index() -> list[dict]:
    files = []
    for p in sorted(SOURCE_DIR.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        name = p.name
        date = extract_date(name) or extract_date(str(rel))
        href = "../" + "/".join(quote(part) for part in rel.parts)
        files.append(
            {
                "name": name,
                "path": str(rel).replace("\\", "/"),
                "href": href,
                "extension": p.suffix.lower().lstrip("."),
                "size_mb": round(p.stat().st_size / 1024 / 1024, 2),
                "date": date or "",
                "bucket": rel.parts[1] if len(rel.parts) > 2 else "根目录",
            }
        )
    return files


def extract_date(text: str) -> str | None:
    normalized = text.replace("－", "-").replace("_", "-")
    patterns = [
        r"(20\d{2})-(\d{1,2})-(\d{1,2})",
        r"(20\d{2})(\d{2})(\d{2})",
        r"(20\d{2})-(\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, normalized)
        if not m:
            continue
        if len(m.groups()) == 3:
            y, mo, d = m.groups()
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        y, mo = m.groups()
        return f"{int(y):04d}-{int(mo):02d}"
    return None


def abnormal_flag(flag: str) -> bool:
    return flag in {"偏高", "偏低", "异常"}


def trend_svg(records: list[dict], item: str, title: str, unit: str = "") -> str:
    points = []
    for r in records:
        if r["item"] == item:
            val = parse_number(r["result"])
            if val is not None:
                points.append((datetime.fromisoformat(r["date"]).toordinal(), val, r["date"]))
    points.sort()
    if len(points) < 2:
        return ""
    w, h, pad = 420, 160, 32
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    if math.isclose(miny, maxy):
        miny -= 1
        maxy += 1
    scale_x = lambda x: pad + (x - minx) / max(1, maxx - minx) * (w - 2 * pad)
    scale_y = lambda y: h - pad - (y - miny) / (maxy - miny) * (h - 2 * pad)
    coords = [(scale_x(x), scale_y(y), y, d) for x, y, d in points]
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y, _, _) in enumerate(coords))
    circles = "\n".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4"><title>{escape(d)}: {val:g}{escape(unit)}</title></circle>'
        for x, y, val, d in coords
    )
    labels = f'<text x="{pad}" y="{h-8}">{escape(points[0][2])}</text><text x="{w-pad}" y="{h-8}" text-anchor="end">{escape(points[-1][2])}</text>'
    return f"""
    <article class="chart-panel">
      <h3>{escape(title)}</h3>
      <svg viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}趋势">
        <line x1="{pad}" y1="{h-pad}" x2="{w-pad}" y2="{h-pad}" />
        <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{h-pad}" />
        <text x="{pad}" y="20">{maxy:g}{escape(unit)}</text>
        <text x="{pad}" y="{h-pad-4}">{miny:g}{escape(unit)}</text>
        <path d="{path}" />
        {circles}
        {labels}
      </svg>
    </article>
    """


def numeric_points(records: list[dict], item: str) -> list[dict]:
    points = []
    for r in records:
        if r["item"] != item:
            continue
        val = parse_number(r["result"])
        if val is None:
            continue
        points.append(
            {
                "date": r["date"],
                "value": val,
                "result": r["result"],
                "unit": r["unit"],
                "reference": r["reference"],
                "flag": r["flag"],
            }
        )
    return sorted(points, key=lambda p: p["date"])


def mini_sparkline(points: list[dict], color: str = "#2563eb") -> str:
    if not points:
        return '<div class="spark-empty">暂无可视化数据</div>'
    if len(points) == 1:
        return f"""
        <svg class="spark" viewBox="0 0 260 78" role="img" aria-label="单次指标">
          <line x1="18" y1="48" x2="242" y2="48" />
          <circle cx="130" cy="48" r="5" style="stroke:{color}" />
          <text x="130" y="70" text-anchor="middle">{escape(points[0]["date"])}</text>
        </svg>
        """

    w, h, pad = 260, 78, 18
    xs = [datetime.fromisoformat(p["date"]).toordinal() for p in points]
    ys = [p["value"] for p in points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    if math.isclose(miny, maxy):
        miny -= 1
        maxy += 1
    def sx(x: int) -> float:
        return pad + (x - minx) / max(1, maxx - minx) * (w - 2 * pad)
    def sy(y: float) -> float:
        return h - pad - (y - miny) / (maxy - miny) * (h - 2 * pad)

    coords = [(sx(x), sy(y), y, p["date"]) for x, y, p in zip(xs, ys, points)]
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y, _, _) in enumerate(coords))
    area = f"{path} L {coords[-1][0]:.1f},{h-pad:.1f} L {coords[0][0]:.1f},{h-pad:.1f} Z"
    dots = "\n".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" style="stroke:{color}"><title>{escape(date)}: {val:g}</title></circle>'
        for x, y, val, date in coords
    )
    return f"""
    <svg class="spark" viewBox="0 0 {w} {h}" role="img" aria-label="指标起伏">
      <path class="spark-area" d="{area}" style="fill:{color};" />
      <path class="spark-line" d="{path}" style="stroke:{color};" />
      {dots}
      <text x="{pad}" y="72">{escape(points[0]["date"][2:])}</text>
      <text x="{w-pad}" y="72" text-anchor="end">{escape(points[-1]["date"][2:])}</text>
    </svg>
    """


def trend_card(records: list[dict], item: str, label: str, unit: str = "") -> str:
    points = numeric_points(records, item)
    if not points:
        return ""
    latest = points[-1]
    previous = points[-2] if len(points) >= 2 else None
    if previous:
        delta = latest["value"] - previous["value"]
        pct = delta / previous["value"] * 100 if previous["value"] else 0
        if delta > 0:
            trend = "较上次升高"
            trend_class = "up"
            arrow = "↑"
        elif delta < 0:
            trend = "较上次下降"
            trend_class = "down"
            arrow = "↓"
        else:
            trend = "较上次持平"
            trend_class = "flat"
            arrow = "→"
        delta_text = f"{arrow} {abs(delta):g}{unit} / {abs(pct):.1f}%"
        compare_text = f"{escape(previous['date'])} → {escape(latest['date'])}"
    else:
        trend = "仅一次记录"
        trend_class = "flat"
        delta_text = "等待后续复查"
        compare_text = escape(latest["date"])

    color = "#dc2626" if latest["flag"] in {"偏高", "偏低", "异常"} else "#059669"
    return f"""
    <article class="trend-card">
      <div class="trend-head">
        <div>
          <span>{escape(label)}</span>
          <strong>{escape(latest["result"])} {escape(latest["unit"] or unit)}</strong>
        </div>
        <em class="flag {status_class(latest["flag"])}">{escape(latest["flag"])}</em>
      </div>
      {mini_sparkline(points, color)}
      <div class="trend-foot">
        <b class="{trend_class}">{trend}：{escape(delta_text)}</b>
        <small>{compare_text}；参考 {escape(latest["reference"] or "未提供")}</small>
      </div>
    </article>
    """


def trend_sentence(records: list[dict], item: str, label: str, unit: str = "") -> str:
    points = numeric_points(records, item)
    if not points:
        return ""
    first = points[0]
    latest = points[-1]
    if len(points) == 1:
        return f"{label}：目前仅 {latest['date']} 一次结构化记录，结果 {latest['result']}{latest['unit'] or unit}，状态为{latest['flag']}。"
    delta = latest["value"] - first["value"]
    direction = "上升" if delta > 0 else "下降" if delta < 0 else "持平"
    pct = abs(delta) / first["value"] * 100 if first["value"] else 0
    return (
        f"{label}：从 {first['date']} 的 {first['result']}{first['unit'] or unit} 到 "
        f"{latest['date']} 的 {latest['result']}{latest['unit'] or unit}，整体{direction} {abs(delta):g}{unit}"
        f"（约 {pct:.1f}%），最近状态为{latest['flag']}。"
    )


def status_class(flag: str) -> str:
    return {
        "正常": "ok",
        "偏高": "high",
        "偏低": "low",
        "异常": "abnormal",
        "未判定": "unknown",
    }.get(flag, "unknown")


def build_html(records: list[dict], files: list[dict]) -> str:
    categories = Counter(r["category"] for r in records)
    flags = Counter(r["flag"] for r in records)
    abnormal = [r for r in records if abnormal_flag(r["flag"])]
    dates = sorted(r["date"] for r in records)
    file_months = Counter((f["date"][:7] if f["date"] else "未识别") for f in files)
    latest_date = dates[-1]
    latest_records = [r for r in records if r["date"] == latest_date]
    latest_abnormal = [r for r in latest_records if abnormal_flag(r["flag"])]
    abnormal_rate = round(len(abnormal) / max(1, len(records)) * 100)
    max_category = max(categories.values()) if categories else 1
    max_month = max(file_months.values()) if file_months else 1

    charts = "\n".join(
        filter(
            None,
            [
                trend_svg(records, "D-二聚体", "D-二聚体趋势", " ng/ml"),
                trend_svg(records, "蛋白酶3抗体", "PR3/蛋白酶3抗体趋势", " mg/L"),
                trend_svg(records, "蛋白S活性", "蛋白S活性趋势", "%"),
                trend_svg(records, "PCT", "降钙素原 PCT 趋势", " ng/mL"),
                trend_svg(records, "GGT", "GGT 趋势", " U/L"),
                trend_svg(records, "ALT", "ALT 趋势", " U/L"),
                trend_svg(records, "尿白细胞试验", "尿白细胞试验趋势", ""),
            ],
        )
    )
    trend_cards = "\n".join(
        filter(
            None,
            [
                trend_card(records, "蛋白酶3抗体", "PR3 / 蛋白酶3抗体", " mg/L"),
                trend_card(records, "D-二聚体", "D-二聚体", " ng/ml FEU"),
                trend_card(records, "蛋白S活性", "蛋白S活性", "%"),
                trend_card(records, "GGT", "GGT", " U/L"),
                trend_card(records, "ALT", "ALT", " U/L"),
                trend_card(records, "PCT", "降钙素原 PCT", " ng/mL"),
                trend_card(records, "白细胞(图像)", "尿白细胞(图像)", " 个/uL"),
                trend_card(records, "细菌(图像)", "尿细菌(图像)", " 个/uL"),
            ],
        )
    )
    analysis_sentences = [
        trend_sentence(records, "蛋白酶3抗体", "PR3/蛋白酶3抗体", " mg/L"),
        trend_sentence(records, "D-二聚体", "D-二聚体", " ng/ml FEU"),
        trend_sentence(records, "蛋白S活性", "蛋白S活性", "%"),
        trend_sentence(records, "GGT", "GGT", " U/L"),
        trend_sentence(records, "ALT", "ALT", " U/L"),
    ]
    analysis_rows = "\n".join(
        f"<li>{escape(s)}</li>" for s in analysis_sentences if s
    )
    latest_urine_summary = (
        f"2026-06-10 尿检：共录入 {len(latest_records)} 条指标，其中 "
        f"{len(latest_abnormal)} 条为异常/偏高；尿蛋白为阴性，尿隐血和尿粒细胞酯酶为阳性(2+)。"
    )
    flag_bars = "\n".join(
        f"""
        <div class="flag-bar">
          <span>{escape(k)}</span>
          <div><i class="{status_class(k)}" style="width:{v / max(1, len(records)) * 100:.1f}%"></i></div>
          <b>{v}</b>
        </div>
        """
        for k, v in flags.most_common()
    )

    category_rows = "\n".join(
        f"""
        <div class="bar-row">
          <div class="bar-label"><span>{escape(k)}</span><strong>{v}</strong></div>
          <div class="bar-track"><div class="bar-fill" style="width:{v / max_category * 100:.1f}%"></div></div>
        </div>
        """
        for k, v in categories.most_common()
    )
    month_rows = "\n".join(
        f"""
        <div class="bar-row compact">
          <div class="bar-label"><span>{escape(k)}</span><strong>{v}</strong></div>
          <div class="bar-track"><div class="bar-fill soft" style="width:{v / max_month * 100:.1f}%"></div></div>
        </div>
        """
        for k, v in sorted(file_months.items())
    )
    abnormal_rows = "\n".join(table_row(r) for r in sorted(abnormal, key=lambda r: (r["date"], r["category"], r["item"]), reverse=True))
    all_rows = "\n".join(table_row(r) for r in records)
    latest_rows = "\n".join(table_row(r) for r in latest_records)
    latest_abnormal_cards = "\n".join(
        f"""
        <article class="signal {status_class(r['flag'])}">
          <span>{escape(r["flag"])}</span>
          <strong>{escape(r["item"])}</strong>
          <p>{escape(r["result"])} {escape(r["unit"])} / 参考 {escape(r["reference"] or "未提供")}</p>
        </article>
        """
        for r in latest_abnormal
    )
    if not latest_abnormal_cards:
        latest_abnormal_cards = '<article class="signal ok"><span>正常</span><strong>最新报告未录入异常项</strong><p>仍建议结合医生意见复核。</p></article>'
    file_rows = "\n".join(
        f'<tr><td>{escape(f["date"])}</td><td>{escape(f["bucket"])}</td><td><a href="{f["href"]}">{escape(f["name"])}</a></td><td>{escape(f["extension"])}</td><td>{f["size_mb"]}</td></tr>'
        for f in files
    )

    data_json = json.dumps(records, ensure_ascii=False)
    files_json = json.dumps(files, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AAV随访数据看板</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --blue: #2563eb;
      --blue-soft: #dbeafe;
      --emerald: #059669;
      --emerald-soft: #d1fae5;
      --red: #dc2626;
      --red-soft: #fee2e2;
      --amber: #d97706;
      --amber-soft: #fef3c7;
      --violet: #7c3aed;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; color: var(--ink); background: var(--bg); }}
    a {{ color: var(--blue); text-decoration: none; }}
    .shell {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    .hero {{ border: 1px solid var(--line); border-radius: 8px; background: linear-gradient(135deg, #ffffff 0%, #eff6ff 55%, #ecfdf5 100%); padding: 24px; box-shadow: 0 10px 30px rgba(15, 23, 42, .06); }}
    .hero-top {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }}
    .eyebrow {{ display: inline-flex; align-items: center; gap: 8px; color: var(--blue); background: rgba(37, 99, 235, .1); border: 1px solid rgba(37, 99, 235, .18); border-radius: 999px; padding: 5px 10px; font-size: 12px; font-weight: 700; }}
    h1 {{ margin: 12px 0 8px; font-size: 30px; line-height: 1.2; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 18px; line-height: 1.35; }}
    h3 {{ margin: 0 0 10px; font-size: 14px; }}
    .note {{ color: var(--muted); max-width: 760px; }}
    .stamp {{ text-align: right; color: var(--muted); font-size: 12px; min-width: 190px; }}
    .stamp strong {{ display: block; color: var(--ink); font-size: 18px; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
    .nav a {{ color: var(--ink); background: rgba(255,255,255,.72); border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; font-weight: 650; }}
    main {{ margin-top: 18px; }}
    .grid {{ display: grid; gap: 16px; }}
    .kpis {{ grid-template-columns: repeat(5, minmax(150px, 1fr)); }}
    .kpi, section, .chart-panel, .signal {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }}
    .kpi {{ padding: 16px; position: relative; overflow: hidden; }}
    .kpi:after {{ content: ""; position: absolute; right: -18px; top: -22px; width: 72px; height: 72px; border-radius: 999px; background: var(--blue-soft); opacity: .65; }}
    .kpi span {{ display: block; color: var(--muted); font-size: 12px; font-weight: 650; }}
    .kpi strong {{ display: block; margin-top: 6px; font-size: 26px; line-height: 1; }}
    .kpi small {{ color: var(--muted); }}
    section {{ padding: 18px; }}
    .section-head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 14px; }}
    .section-head p {{ margin: 4px 0 0; color: var(--muted); }}
    .two {{ grid-template-columns: minmax(0, 1.55fr) minmax(320px, .9fr); }}
    .three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .charts {{ grid-template-columns: repeat(3, minmax(260px, 1fr)); }}
    .signals {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .trend-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .signal {{ padding: 14px; border-left-width: 4px; }}
    .signal span {{ display: inline-flex; border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 700; }}
    .signal strong {{ display: block; margin-top: 10px; }}
    .signal p {{ margin: 4px 0 0; color: var(--muted); }}
    .signal.high, .signal.low, .signal.abnormal {{ border-left-color: var(--red); background: linear-gradient(180deg, #fff 0%, #fff7f7 100%); }}
    .signal.ok {{ border-left-color: var(--emerald); }}
    .signal.unknown {{ border-left-color: var(--amber); }}
    .pill {{ display: inline-flex; border-radius: 999px; padding: 4px 9px; background: var(--blue-soft); color: var(--blue); font-weight: 700; font-size: 12px; }}
    .callout {{ border: 1px dashed #93c5fd; background: #eff6ff; color: #1e3a8a; border-radius: 8px; padding: 12px 14px; }}
    .callout strong {{ display: block; margin-bottom: 3px; color: #1d4ed8; }}
    .analysis-list {{ margin: 0; padding-left: 18px; color: var(--ink); }}
    .analysis-list li {{ margin: 0 0 10px; color: #334155; }}
    .flag-bars {{ display: grid; gap: 11px; }}
    .flag-bar {{ display: grid; grid-template-columns: 58px 1fr 36px; gap: 10px; align-items: center; color: var(--muted); }}
    .flag-bar div {{ height: 9px; background: #eef2f7; border-radius: 999px; overflow: hidden; }}
    .flag-bar i {{ display: block; height: 100%; border-radius: inherit; min-width: 3px; }}
    .flag-bar i.ok {{ background: var(--emerald); }}
    .flag-bar i.high, .flag-bar i.low, .flag-bar i.abnormal {{ background: var(--red); }}
    .flag-bar i.unknown {{ background: var(--amber); }}
    .trend-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-width: 0; }}
    .trend-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }}
    .trend-head span {{ display: block; color: var(--muted); font-size: 12px; font-weight: 700; }}
    .trend-head strong {{ display: block; margin-top: 4px; font-size: 20px; line-height: 1.15; }}
    .trend-head em {{ font-style: normal; flex: 0 0 auto; }}
    .spark {{ width: 100%; height: 78px; margin-top: 8px; }}
    .spark line {{ stroke: var(--line); }}
    .spark-area {{ opacity: .10; }}
    .spark-line {{ fill: none; stroke-width: 3; }}
    .spark circle {{ fill: #fff; stroke-width: 2; }}
    .spark text {{ fill: var(--muted); font-size: 10px; }}
    .spark-empty {{ margin-top: 10px; color: var(--muted); height: 78px; display: flex; align-items: center; }}
    .trend-foot {{ border-top: 1px solid var(--line); padding-top: 10px; margin-top: 6px; display: grid; gap: 2px; }}
    .trend-foot b {{ font-size: 12px; }}
    .trend-foot small {{ color: var(--muted); }}
    .trend-foot .up {{ color: var(--red); }}
    .trend-foot .down {{ color: var(--emerald); }}
    .trend-foot .flat {{ color: var(--amber); }}
    svg {{ width: 100%; height: auto; }}
    svg line {{ stroke: var(--line); }}
    svg path {{ fill: none; stroke: var(--blue); stroke-width: 3; }}
    svg circle {{ fill: #fff; stroke: var(--blue); stroke-width: 2; }}
    svg text {{ fill: var(--muted); font-size: 11px; }}
    .chart-panel {{ padding: 16px; }}
    .toolbar {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 6px 0 12px; }}
    input, select, button {{ border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; background: #fff; color: var(--ink); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; background: #f8fafc; position: sticky; top: 0; z-index: 1; }}
    .table-wrap {{ max-height: 520px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }}
    .flag {{ display: inline-block; min-width: 44px; text-align: center; border-radius: 999px; padding: 2px 8px; font-size: 12px; }}
    .ok {{ color: var(--emerald); background: var(--emerald-soft); }}
    .high, .low, .abnormal {{ color: var(--red); background: var(--red-soft); }}
    .unknown {{ color: var(--amber); background: var(--amber-soft); }}
    .bar-row {{ margin-bottom: 12px; }}
    .bar-row.compact {{ margin-bottom: 10px; }}
    .bar-label {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 6px; color: var(--muted); }}
    .bar-label span {{ color: var(--ink); }}
    .bar-track {{ height: 8px; background: #eef2f7; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--blue), var(--emerald)); border-radius: inherit; }}
    .bar-fill.soft {{ background: linear-gradient(90deg, #93c5fd, #a7f3d0); }}
    footer {{ margin-top: 18px; padding: 16px 0 4px; color: var(--muted); }}
    @media (max-width: 980px) {{ .shell {{ padding: 16px; }} .hero-top {{ flex-direction: column; }} .stamp {{ text-align: left; }} .kpis, .two, .three, .charts, .signals, .trend-grid {{ grid-template-columns: 1fr; }} h1 {{ font-size: 24px; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-top">
        <div>
          <div class="eyebrow">AAV 随访资料 · 本地健康档案</div>
          <h1>AAV随访数据看板</h1>
          <div class="note">整合检查报告、趋势指标和原始文件索引。数据用于资料整理和复诊沟通，不能替代医生诊断或用药建议。</div>
        </div>
        <div class="stamp">
          <span>最新报告日期</span>
          <strong>{escape(latest_date)}</strong>
          <span>{len(latest_records)} 条本次指标</span>
        </div>
      </div>
      <nav class="nav">
        <a href="#overview">总览</a>
        <a href="#analysis">分析总结</a>
        <a href="#latest">最新报告</a>
        <a href="#signals">异常提醒</a>
        <a href="#fluctuation">指标起伏</a>
        <a href="#trends">趋势图</a>
        <a href="#details">指标明细</a>
        <a href="#files">原始资料</a>
      </nav>
    </header>

  <main id="overview">
    <div class="grid kpis">
      <div class="kpi"><span>结构化指标</span><strong>{len(records)}</strong><small>已录入看板</small></div>
      <div class="kpi"><span>异常/偏离项目</span><strong>{len(abnormal)}</strong><small>占 {abnormal_rate}%</small></div>
      <div class="kpi"><span>原始资料文件</span><strong>{len(files)}</strong><small>报告、截图、PDF</small></div>
      <div class="kpi"><span>随访时间范围</span><strong>{escape(dates[0])}</strong><small>至 {escape(dates[-1])}</small></div>
      <div class="kpi"><span>最新报告异常项</span><strong>{len(latest_abnormal)}</strong><small>{escape(latest_date)}</small></div>
    </div>

    <section id="analysis" style="margin-top:16px;">
      <div class="section-head">
        <div>
          <h2>随访分析总结</h2>
          <p>根据已结构化数据自动生成，重点看方向、幅度和是否仍偏离参考范围。</p>
        </div>
        <span class="pill">自动汇总</span>
      </div>
      <div class="grid two">
        <div class="callout">
          <strong>关键变化</strong>
          <ul class="analysis-list">
            {analysis_rows}
            <li>{escape(latest_urine_summary)}</li>
          </ul>
        </div>
        <div>
          <h3>指标状态分布</h3>
          <div class="flag-bars">{flag_bars}</div>
        </div>
      </div>
    </section>

    <section id="latest" style="margin-top:16px;">
      <div class="section-head">
        <div>
          <h2>最新报告：尿沉渣定量检测 / 尿干化学检测</h2>
          <p>中山医一院，采集时间 2026-06-10 08:26，报告时间 2026-06-10 08:50。</p>
        </div>
        <span class="pill">已加入仓库</span>
      </div>
      <div class="grid signals">{latest_abnormal_cards}</div>
      <div class="callout" style="margin-top:14px;">
        <strong>本次尿检提示项</strong>
        白细胞、细菌、黏液丝、尿隐血和尿粒细胞酯酶已标记为异常/偏高；尿蛋白为阴性。建议作为复诊沟通素材，结合症状、用药和医生判断复核。
      </div>
      <div class="table-wrap" style="margin-top:14px;"><table><thead>{table_head()}</thead><tbody>{latest_rows}</tbody></table></div>
    </section>

    <div class="grid two" style="margin-top:16px;">
      <section id="signals">
        <div class="section-head">
          <div>
            <h2>异常项目速览</h2>
            <p>按日期倒序展示偏高、偏低和阳性项目。</p>
          </div>
          <span class="pill">{len(abnormal)} 项</span>
        </div>
        <div class="table-wrap"><table><thead>{table_head()}</thead><tbody>{abnormal_rows}</tbody></table></div>
      </section>
      <section>
        <div class="section-head">
          <div>
            <h2>分类分布</h2>
            <p>用于快速定位资料集中在哪些检查方向。</p>
          </div>
        </div>
        {category_rows}
      </section>
    </div>

    <section id="fluctuation" style="margin-top:16px;">
      <div class="section-head">
        <div>
          <h2>关键指标起伏</h2>
          <p>每张卡片显示最新值、较上次变化，以及已有记录的迷你趋势线。</p>
        </div>
      </div>
      <div class="grid trend-grid">{trend_cards}</div>
    </section>

    <section id="trends" style="margin-top:16px;">
      <div class="section-head">
        <div>
          <h2>核心趋势图</h2>
          <p>展示已有连续数据的指标，鼠标悬停可查看单点数值。</p>
        </div>
      </div>
      <div class="grid charts">{charts}</div>
    </section>

    <section id="details" style="margin-top:16px;">
      <div class="section-head">
        <div>
          <h2>结构化指标明细</h2>
          <p>支持按状态筛选，也可以搜索项目、报告或分类。</p>
        </div>
      </div>
      <div class="toolbar">
        <input id="metricSearch" type="search" placeholder="搜索项目、报告、分类" />
        <select id="flagFilter">
          <option value="">全部状态</option>
          <option value="偏高">偏高</option>
          <option value="偏低">偏低</option>
          <option value="异常">异常</option>
          <option value="正常">正常</option>
          <option value="未判定">未判定</option>
        </select>
      </div>
      <div class="table-wrap"><table id="metricTable"><thead>{table_head()}</thead><tbody>{all_rows}</tbody></table></div>
    </section>

    <section id="files" style="margin-top:16px;">
      <div class="section-head">
        <div>
          <h2>原始资料索引</h2>
          <p>所有原始报告都保留链接，便于回看原件。</p>
        </div>
      </div>
      <div class="grid two">
        <div class="table-wrap"><table id="fileTable"><thead><tr><th>日期</th><th>目录</th><th>文件</th><th>类型</th><th>MB</th></tr></thead><tbody>{file_rows}</tbody></table></div>
        <div><h3>文件月份分布</h3>{month_rows}</div>
      </div>
    </section>
  </main>
  <footer>最后生成：{datetime.now().strftime("%Y-%m-%d %H:%M")}。建议后续补充 OCR 后再做完整医学趋势分析。</footer>
  </div>
  <script>
    const records = {data_json};
    const files = {files_json};
    const tbody = document.querySelector("#metricTable tbody");
    const search = document.querySelector("#metricSearch");
    const flag = document.querySelector("#flagFilter");
    function cls(x) {{ return {{ "正常":"ok", "偏高":"high", "偏低":"low", "异常":"abnormal", "未判定":"unknown" }}[x] || "unknown"; }}
    function render() {{
      const q = search.value.trim().toLowerCase();
      const f = flag.value;
      tbody.innerHTML = records.filter(r => (!f || r.flag === f) && (!q || JSON.stringify(r).toLowerCase().includes(q))).map(r => `
        <tr><td>${{r.date}}</td><td>${{r.category}}</td><td>${{r.report}}</td><td>${{r.item}}</td><td><strong>${{r.result}}</strong> ${{r.unit}}</td><td>${{r.reference}}</td><td><span class="flag ${{cls(r.flag)}}">${{r.flag}}</span></td><td>${{r.source}}</td></tr>
      `).join("");
    }}
    search.addEventListener("input", render);
    flag.addEventListener("change", render);
  </script>
</body>
</html>"""


def table_head() -> str:
    return "<tr><th>日期</th><th>分类</th><th>报告</th><th>项目</th><th>结果</th><th>参考范围</th><th>状态</th><th>来源</th></tr>"


def table_row(r: dict) -> str:
    return (
        "<tr>"
        f"<td>{escape(r['date'])}</td>"
        f"<td>{escape(r['category'])}</td>"
        f"<td>{escape(r['report'])}</td>"
        f"<td>{escape(r['item'])}</td>"
        f"<td><strong>{escape(r['result'])}</strong> {escape(r['unit'])}</td>"
        f"<td>{escape(r['reference'])}</td>"
        f"<td><span class=\"flag {status_class(r['flag'])}\">{escape(r['flag'])}</span></td>"
        f"<td>{escape(r['source'])}</td>"
        "</tr>"
    )


def write_outputs(records: list[dict], files: list[dict]) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    (OUT_DIR / "health_metrics.json").write_text(
        json.dumps({"generated_at": generated_at, "metrics": records, "files": files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (OUT_DIR / "health_metrics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    (OUT_DIR / "index.html").write_text(build_html(records, files), encoding="utf-8")


def main() -> None:
    records = make_records()
    files = file_index()
    write_outputs(records, files)
    print(json.dumps({"metrics": len(records), "files": len(files), "out": str(OUT_DIR)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
