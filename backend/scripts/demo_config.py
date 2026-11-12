"""seed 演示配置：订阅源 / 单集 / show notes / 历史批次 的唯一定义处。

数值不是随手写的——它们被 seed 契约与主流程验收锁死：
  feeds=6  episodes=48  chapters=260  issues=22（12 乱序 + 3 重叠 + 4 未识别 + 3 缺口）
主流程：
  采集 48 集 → 新增 3（水位线后新到达） / 更新 5（平台简介变更） / 不变 40
  解析 260 行 → unparsed 4
  修 EP-044（3 条乱序纠正、1 条重叠合并、「约 12 分钟处」→720s）
  → 22 个 issue 里 gap_warning 3 条
演示数据全部由确定性规则生成（无随机数），两次 seed 逐字一致。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DEMO_PASSWORD = "Demo@2026"
STUDIO_NAME = "声景内容工作室 · 节目运营组"

DEMO_USERS: list[tuple[str, str, str]] = [
    ("admin@podcastdig.io", "陈砚秋", "admin"),
    ("analyst@podcastdig.io", "林向北", "analyst"),
    ("viewer@podcastdig.io", "周夏", "viewer"),
]

# 演示用时间基准（seed 固定，保证 published_on / 批次时间可复现）
ANCHOR_DATE = date(2026, 9, 16)


@dataclass(frozen=True)
class FeedSpec:
    code: str
    name: str
    show_name: str
    kind: str
    url: str
    fixture_file: str
    cadence: str
    host: str
    note: str


@dataclass(frozen=True)
class EpisodeSpec:
    code: str
    feed_code: str
    guid: str
    season: int
    episode_no: int
    title: str
    duration_seconds: int
    published_on: date
    summary: str
    summary_new: str
    show_notes: str
    cover_hint: str
    ingest_state: str


FEEDS: list[FeedSpec] = [
    FeedSpec(
        code="swing",
        name="商业访谈 · 柜台之后",
        show_name="柜台之后",
        kind="rss",
        url="https://feeds.podcastdig.io/swing.xml",
        fixture_file="swing.xml",
        cadence="每周三 09:00",
        host="陈砚秋",
        note="RSS 2.0 + itunes 扩展；show notes 用 mm:ss 时间码",
    ),
    FeedSpec(
        code="techweekly",
        name="科技周报 · 信号与噪声",
        show_name="信号与噪声",
        kind="rss",
        url="https://feeds.podcastdig.io/techweekly.xml",
        fixture_file="techweekly.xml",
        cadence="每周五 18:00",
        host="林向北",
        note="RSS 2.0；经常在正文里贴 1h02m 这类非常规时间码",
    ),
    FeedSpec(
        code="studio",
        name="录音棚夜话",
        show_name="录音棚夜话",
        kind="platform",
        url="https://open.podcastdig.io/v1/shows/studio",
        fixture_file="studio.json",
        cadence="每周一 21:00",
        host="老周",
        note="平台 JSON 接口；章节写成 @mm:ss 锚点",
    ),
    FeedSpec(
        code="field",
        name="田野录音笔记",
        show_name="田野录音笔记",
        kind="platform",
        url="https://open.podcastdig.io/v1/shows/field",
        fixture_file="field.json",
        cadence="每两周 周四 07:30",
        host="阿岚",
        note="平台 JSON 接口；中文时间码 X分Y秒 为主",
    ),
    FeedSpec(
        code="longform",
        name="长谈 · 声音档案",
        show_name="长谈",
        kind="apple",
        url="https://catalog.podcastdig.io/apple/longform",
        fixture_file="longform.html",
        cadence="每月 1 日",
        host="陈砚秋 / 老周",
        note="目录 HTML；长节目用 hh:mm:ss，出现过 1:11 这类歧义写法",
    ),
    FeedSpec(
        code="citywalk",
        name="城市漫游 · 街声",
        show_name="城市漫游",
        kind="rss",
        url="https://feeds.podcastdig.io/citywalk.xml",
        fixture_file="citywalk.xml",
        cadence="每周六 08:00",
        host="阿岚",
        note="RSS 2.0；口播稿常写「约 N 分钟处」",
    ),
]

FEED_BY_CODE = {feed.code: feed for feed in FEEDS}

_EPISODE_TITLES: dict[str, list[str]] = {
    "swing": [
        "咖啡连锁的第三次库存危机",
        "从便利店看城市消费分层",
        "一条毛巾的供应链账本",
        "烘焙品牌如何熬过淡季",
        "生鲜前置仓的单均成本",
        "新茶饮加盟商的回本周期",
        "社区团购退潮后的团长们",
        "区域乳企的冷链算术",
    ],
    "techweekly": [
        "端侧模型的算力账",
        "折叠屏铰链的十次迭代",
        "卫星互联网的最后一公里",
        "电池回收的灰色地带",
        "AR 眼镜的光学难题",
        "大模型推理的成本拐点",
        "芯片封装的产能争夺",
        "智能家居的协议混战",
    ],
    "studio": [
        "母带到底该压多狠",
        "人声齿音的十种处理",
        "一间小棚的声学改造",
        "混音师的监听选择",
        "现场收音的风噪对抗",
        "采样率焦虑症",
        "插件越买越不会混",
        "播客响度标准之争",
    ],
    "field": [
        "台风过境后的红树林",
        "清晨五点的渔市",
        "山间公路的蝉鸣",
        "老城区的水井声",
        "高铁站的广播回响",
        "稻田里的灌溉渠",
        "雪后寺庙的钟声",
        "夜市收摊前的最后半小时",
    ],
    "longform": [
        "三小时聊透播客商业化",
        "从电台到播客的三十年",
        "内容团队的现金流管理",
        "音频平台的推荐机制",
        "一档节目的十年",
        "采访者的提问手艺",
        "声音纪录片的伦理边界",
        "播客剪辑的节奏感",
    ],
    "citywalk": [
        "城市漫游 · 潮州：牌坊街的午后",
        "城市漫游 · 绍兴：乌篷船与黄酒",
        "城市漫游 · 景德镇：窑火不熄",
        "城市漫游 · 泉州：西街的清晨与蟳埔的簪花",
        "城市漫游 · 大理：苍山下的市集",
        "城市漫游 · 扬州：早茶与澡堂",
        "城市漫游 · 福州：上下杭的雨",
        "城市漫游 · 建水：米轨与豆腐",
    ],
}

_CHAPTER_POOL: dict[str, list[str]] = {
    "swing": [
        "开场：这一集我们聊什么",
        "嘉宾自我介绍与门店背景",
        "库存周转的三条曲线",
        "加盟商的真实账本",
        "供应链金融的利息成本",
        "区域仓配的时效博弈",
        "促销节点的备货判断",
        "会员体系的复购贡献",
        "人力成本与排班颗粒度",
        "从单店模型到城市模型",
        "失败案例复盘",
        "听众提问：要不要开第二家",
        "数据口径问答",
        "片尾：下期预告",
        "广告位与赞助说明",
        "补录：嘉宾补充的两点",
        "编辑手记",
        "延伸阅读清单",
    ],
    "techweekly": [
        "本周信号：三条新闻",
        "端侧推理的功耗曲线",
        "供应链口径的一次澄清",
        "拆解成本结构",
        "对比三家方案",
        "开发者反馈",
        "专利与标准之争",
        "一位听众的不同意见",
        "上周更正",
        "数据和图表说明",
        "采访片段：产线工程师",
        "行业历史回顾",
        "风险提示",
        "下期选题投票",
        "片尾曲与致谢",
        "加更说明",
        "参考链接",
        "编辑手记",
    ],
    "studio": [
        "开场：今天棚里只开了两盏灯",
        "监听校准的十分钟",
        "压缩器的启动与释放",
        "人声链路的顺序问题",
        "齿音处理的两个流派",
        "混响的空间感",
        "母带响度的取舍",
        "A/B 对比试听",
        "设备清单与预算",
        "听众投稿的混音片段",
        "常见误区",
        "监听音量与听觉疲劳",
        "收尾：把工程文件存三份",
        "赞助口播录制花絮",
        "补录：插件版本差异",
        "延伸阅读",
        "编辑手记",
        "下期预告",
    ],
    "field": [
        "开场：录音笔开机",
        "环境声铺底",
        "第一段现场",
        "与当地人对话",
        "路线与天气",
        "设备与防风",
        "安静下来听三十秒",
        "声音里的一段历史",
        "被误认成设备故障的蝉鸣",
        "雨声与屋檐",
        "返程路上的复盘",
        "素材取舍",
        "后期处理说明",
        "下一条线索",
        "致谢向导",
        "补录：第二天清晨",
        "延伸收听",
        "编辑手记",
    ],
    "longform": [
        "开场与嘉宾介绍",
        "从电台时代讲起",
        "第一次商业化尝试",
        "平台分成结构",
        "团队扩张的代价",
        "广告与内容边界",
        "听众增长曲线",
        "一次失败的付费尝试",
        "现金流最紧的那个月",
        "与资本的三次对话",
        "内容的工业化与手作感",
        "给新节目的建议",
        "嘉宾反问主持人",
        "三小时里被剪掉的段落",
        "片尾：书单与节目推荐",
        "制作团队名单",
        "补录说明",
        "编辑手记",
    ],
    "citywalk": [
        "开场：城市醒来之前",
        "街口的第一家早点摊",
        "老建筑的立面细节",
        "一段方言录音",
        "巷子里的手艺人",
        "河边与桥",
        "菜市场的声音层次",
        "午后的茶馆",
        "当地人的路线建议",
        "一块碑的来历",
        "雨突然下了",
        "收尾：把声音留给街道",
        "交通与时长说明",
        "下期城市预告",
        "致谢受访者",
        "补录：返程时的车站广播",
        "延伸书单",
        "编辑手记",
    ],
}

# 每集章节行数（含重复行 / 未识别行），合计 260
_CHAPTER_COUNTS: dict[str, int] = {
    "EP-009": 7,
    "EP-012": 7,
    "EP-027": 7,
    "EP-031": 7,
    "EP-035": 9,
    "EP-036": 9,
    "EP-044": 9,
}

# 尾部 k+1 行整体右移一位（末行提到最前）→ 恰好 k 条乱序，且不影响更早的行
_ROTATE: dict[str, int] = {"EP-012": 5, "EP-027": 4, "EP-044": 3}
# 插入一条同时间点的重复行：code -> (抢同一个时间点, 重复条标题)
_DUPLICATE: dict[str, tuple[int, str]] = {
    "EP-012": (2225, "平台重复条目"),
    "EP-027": (2225, "平台重复条目"),
    "EP-044": (2870, "蟳埔女的簪花围"),
}
# 在第 i 行之后整体后移 extra 秒 → 造一个 > 8 分钟的缺口
_GAP_AFTER: dict[str, tuple[int, int]] = {
    "EP-005": (2, 640),
    "EP-019": (2, 640),
    "EP-038": (2, 640),
}

_UNPARSED_TAIL: dict[str, list[str]] = {
    "EP-009": [
        "1h02m 听众问答（时间码格式未识别）",
        "1h18m 片尾曲与下期预告（时间码格式未识别）",
    ],
    "EP-031": [
        "0h28m 设备清单（时间码格式未识别）",
        "0h52m 返程复盘（时间码格式未识别）",
    ],
}

# 显式指定时间点（用于中文时间码 / 歧义写法这类需要固定位置的集）
_STARTS_OVERRIDE: dict[str, list[int]] = {
    "EP-009": [60, 490, 920, 1350, 1780],
    "EP-031": [60, 490, 920, 1350, 1780],
    "EP-044": [60, 350, 720, 1150, 1580, 2010, 2440, 2870],
    "EP-035": [30, 71, 490, 920, 1350, 1780, 2210, 2640, 3070],
    "EP-036": [60, 490, 920, 1350, 1780, 2210, 2640, 3070, 3500],
}

# 指定某一时间点的原始时间码写法（覆盖默认格式化）
_RAW_OVERRIDE: dict[str, dict[int, str]] = {
    "EP-044": {720: "约 12 分钟处 骑楼下的茶摊与老醋"},
    "EP-035": {71: "1:11 听众来信（时间读法存疑）"},
}

# 时间码写法特殊的两集：长谈 EP-036 用「X时Y分Z秒」，EP-035 用 hh:mm:ss + 一条歧义
_CN_HOUR_EPISODES = {"EP-036"}

# 夹具里被平台改写简介的 5 集（采集时计为「更新」）
_UPDATED_SUMMARIES = {"EP-003", "EP-014", "EP-022", "EP-030", "EP-042"}

# 水位线之后新到达、尚未入库采集的 3 集（采集时计为「新增」）
_PENDING_EPISODES = {"EP-013", "EP-029", "EP-046"}


def _mmss(seconds: int) -> str:
    minutes, secs = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def _hhmmss(seconds: int) -> str:
    hours, rest = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _cn_clock(seconds: int, with_hours: bool = False) -> str:
    hours, rest = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(rest, 60)
    if with_hours or hours:
        return f"{hours}时{minutes:02d}分{secs:02d}秒"
    return f"{minutes}分{secs:02d}秒"


def _format_stamp(seconds: int, feed_code: str, episode_code: str) -> str:
    if feed_code == "studio":
        return f"@{_mmss(seconds)}"
    if feed_code == "field" and episode_code not in _CN_HOUR_EPISODES:
        # 「X分Y秒」写法（不带小时）
        return _cn_clock(seconds)
    if feed_code == "longform":
        if episode_code in _CN_HOUR_EPISODES:
            # 「X时Y分Z秒」写法，0 时也写全，符合长节目 show notes 习惯
            return _cn_clock(seconds, with_hours=True)
        return _hhmmss(seconds)
    if seconds >= 3600:
        return _hhmmss(seconds)
    return _mmss(seconds)


def _base_starts(count: int, duration: int) -> list[int]:
    step = max(120, (duration - 300) // max(1, count))
    return [60 + index * step for index in range(count)]


def _episode_duration(code: str, feed_index: int, episode_no: int, rows: int) -> int:
    special = {
        "EP-005": 2600,
        "EP-009": 3310,
        "EP-012": 2900,
        "EP-019": 2600,
        "EP-027": 2900,
        "EP-031": 3310,
        "EP-035": 4170,
        "EP-036": 4400,
        "EP-038": 2600,
        "EP-044": 3540,
    }
    if code in special:
        return special[code]
    if rows == 6:
        return 2900 + (episode_no % 4) * 40
    return 2450 + (feed_index * 3 + episode_no) % 5 * 40


def _build_rows(spec_code: str, feed_code: str, duration: int, rows: int, episode_no: int) -> tuple[list[dict], list[str]]:
    """返回 (章节行, 未识别尾巴行)。行里 start 可为 None（未识别）。"""
    pool = _CHAPTER_POOL[feed_code]

    tail_count = len(_UNPARSED_TAIL.get(spec_code, []))
    duplicate_count = 1 if spec_code in _DUPLICATE else 0
    unique_rows = max(1, rows - tail_count - duplicate_count)

    if spec_code in _STARTS_OVERRIDE:
        starts = list(_STARTS_OVERRIDE[spec_code])
    else:
        starts = _base_starts(unique_rows, duration)

    rows_out: list[dict] = []
    for index, start in enumerate(starts):
        title = pool[(episode_no * 3 + index) % len(pool)]
        rows_out.append({"start": start, "title": title, "raw": None})

    if spec_code in _ROTATE:
        count = _ROTATE[spec_code]
        block = rows_out[len(rows_out) - (count + 1):]
        rows_out = [*rows_out[: len(rows_out) - (count + 1)], block[-1], *block[:-1]]

    if spec_code in _DUPLICATE:
        duplicate_start, duplicate_title = _DUPLICATE[spec_code]
        position = next(
            index for index, row in enumerate(rows_out) if row["start"] == duplicate_start
        )
        rows_out.insert(
            position + 1,
            {"start": duplicate_start, "title": duplicate_title, "raw": None, "duplicate": True},
        )

    if spec_code in _GAP_AFTER:
        gap_index, extra = _GAP_AFTER[spec_code]
        for index in range(gap_index + 1, len(rows_out)):
            rows_out[index]["start"] = rows_out[index]["start"] + extra

    overrides = _RAW_OVERRIDE.get(spec_code, {})
    for row in rows_out:
        start = row["start"]
        raw = None if row.get("duplicate") else overrides.get(start)
        if raw is None:
            raw = f"{_format_stamp(start, feed_code, spec_code)} {row['title']}"
        row["raw"] = raw

    tail = _UNPARSED_TAIL.get(spec_code, [])
    for raw in tail:
        rows_out.append({"start": None, "title": raw, "raw": raw})

    return rows_out, tail


def _build_summary(title: str, feed: FeedSpec, episode_no: int, track: str) -> str:
    return (
        f"{feed.show_name} 第 {episode_no} 集：{title}。"
        f"本期从{track}切入，聊了三件具体的事和一组可复用的口径，"
        f"适合在通勤或剪辑时收听。"
    )


_TRACK_HINT = {
    "swing": "门店账本与供应链成本",
    "techweekly": "本周技术信号与拆解数据",
    "studio": "录音棚工序与听感判断",
    "field": "现场声音与在地经验",
    "longform": "一场没有剪辑的长对话",
    "citywalk": "一条街道的声音层次",
}


def _build_episodes() -> list[EpisodeSpec]:
    episodes: list[EpisodeSpec] = []
    code_no = 0
    for feed_index, feed in enumerate(FEEDS):
        titles = _EPISODE_TITLES[feed.code]
        for index, title in enumerate(titles):
            code_no += 1
            code = f"EP-{code_no:03d}"
            rows = _CHAPTER_COUNTS.get(code, 5)
            duration = _episode_duration(code, feed_index, index + 1, rows)
            published = ANCHOR_DATE + timedelta(days=feed_index + 7 * index)
            chapter_rows, tail = _build_rows(code, feed.code, duration, rows, index + 1)

            header = [
                title,
                f"节目：{feed.show_name} ｜ 时长 {_hhmmss(duration)} ｜ 发布 {published.isoformat()}",
                "",
                f"本期嘉宾：{feed.host} ｜ 剪辑：老周 ｜ 选题：阿岚",
                "本期内容：",
            ]
            body = [row["raw"] for row in chapter_rows]
            footer = [
                "",
                "剪辑 / 混音：老周",
                "选题：阿岚",
                "（章节时间码来自 show notes 原文，未经二次加工）",
            ]
            show_notes = "\n".join([*header, *body, *footer])

            summary = _build_summary(title, feed, index + 1, _TRACK_HINT[feed.code])
            summary_new = summary
            if code in _UPDATED_SUMMARIES:
                summary_new = (
                    summary
                    + " 【2026-11 平台修订】补充了嘉宾更正的一处口径，并追加两条参考链接。"
                )

            episodes.append(
                EpisodeSpec(
                    code=code,
                    feed_code=feed.code,
                    guid=f"podcastdig:{feed.code}:s{feed_index + 2:02d}e{index + 1:03d}",
                    season=feed_index + 2,
                    episode_no=index + 1,
                    title=title,
                    duration_seconds=duration,
                    published_on=published,
                    summary=summary,
                    summary_new=summary_new,
                    show_notes=show_notes,
                    cover_hint="REEL",
                    ingest_state="pending" if code in _PENDING_EPISODES else "synced",
                )
            )
    return episodes


EPISODES: list[EpisodeSpec] = _build_episodes()
EPISODE_BY_CODE = {episode.code: episode for episode in EPISODES}

# 已跑过的历史批次（seed 写入，供「采集任务」页面有上下文）
SEED_TASKS: list[dict] = [
    {
        "code": "DG-0001",
        "mode": "ingest",
        "status": "success",
        "feed_scope": "all",
        "triggered_by": "analyst@podcastdig.io",
        "triggered_role": "analyst",
        "feeds_scanned": 6,
        "episodes_scanned": 48,
        "episodes_new": 0,
        "episodes_updated": 2,
        "episodes_unchanged": 46,
        "chapters_parsed": 0,
        "unparsed_chapters": 0,
        "issues_found": 0,
        "duration_ms": 1840,
        "started_ago_minutes": 26 * 60,
        "log_lines": [
            "RSS 3 个源，平台 2 个源，目录 1 个源",
            "水位线 2026-11-05T09:00:00+08:00",
            "swing.xml 命中 8 条（更新 1）",
            "techweekly.xml 命中 8 条（更新 1）",
            "citywalk.xml 命中 8 条（更新 0）",
            "studio.json 命中 8 条（更新 0）",
            "field.json 命中 8 条（更新 0）",
            "longform.html 命中 8 条（更新 0）",
        ],
    },
    {
        "code": "DG-0002",
        "mode": "parse",
        "status": "success",
        "feed_scope": "all",
        "triggered_by": "analyst@podcastdig.io",
        "triggered_role": "analyst",
        "feeds_scanned": 6,
        "episodes_scanned": 48,
        "episodes_new": 0,
        "episodes_updated": 0,
        "episodes_unchanged": 0,
        "chapters_parsed": 260,
        "unparsed_chapters": 4,
        "issues_found": 22,
        "duration_ms": 2260,
        "started_ago_minutes": 25 * 60,
        "log_lines": [
            "解析 48 集 / 260 行章节",
            "时间码规则命中：mm:ss 178，hh:mm:ss 46，分秒 20，@ 8，约 N 分钟 1",
            "未识别 4 行（EP-009 2 行 / EP-031 2 行）",
            "不变量校验：乱序 12 / 重叠 3 / 缺口 3 / 未识别 4",
        ],
    },
    {
        "code": "DG-0003",
        "mode": "both",
        "status": "success",
        "feed_scope": "all",
        "triggered_by": "admin@podcastdig.io",
        "triggered_role": "admin",
        "feeds_scanned": 6,
        "episodes_scanned": 48,
        "episodes_new": 0,
        "episodes_updated": 0,
        "episodes_unchanged": 48,
        "chapters_parsed": 260,
        "unparsed_chapters": 4,
        "issues_found": 22,
        "duration_ms": 3120,
        "started_ago_minutes": 3 * 24 * 60,
        "log_lines": ["采集无新增", "解析 260 行，异常仍为 22 条", "等待人工处置 EP-044 / EP-012 / EP-027"],
    },
    {
        "code": "DG-0004",
        "mode": "parse",
        "status": "failed",
        "feed_scope": "field,longform",
        "triggered_by": "analyst@podcastdig.io",
        "triggered_role": "analyst",
        "feeds_scanned": 2,
        "episodes_scanned": 16,
        "episodes_new": 0,
        "episodes_updated": 0,
        "episodes_unchanged": 0,
        "chapters_parsed": 46,
        "unparsed_chapters": 2,
        "issues_found": 6,
        "duration_ms": 88120,
        "started_ago_minutes": 5 * 24 * 60,
        "log_lines": [
            "field.json 命中 8 条",
            "longform.html 取回超时，重试 3 次后放弃",
            "批次标记失败：16 集中 8 集未解析",
        ],
        "error_text": "longform.html 取回超时（read timeout 30s × 3），批次回滚未解析部分",
    },
]

SEED_AUDIT: list[tuple[str, str, str, str, str, str, dict]] = [
    (
        "seed:audit:1",
        "admin@podcastdig.io",
        "admin",
        "feed.create",
        "feed",
        "swing",
        {"kind": "rss", "cadence": "每周三 09:00"},
    ),
    (
        "seed:audit:2",
        "analyst@podcastdig.io",
        "analyst",
        "chapter.normalize",
        "episode",
        "EP-012",
        {"reordered": 5, "merged": 1, "folded": 0},
    ),
]
