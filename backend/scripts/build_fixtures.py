"""生成确定性订阅源夹具：RSS XML / 平台 JSON / 目录 HTML。

夹具是「平台上真实长什么样」的静态快照，采集任务只读这些文件，不访问网络。
改完 demo_config 后重跑本脚本即可。

用法：cd backend && python3 scripts/build_fixtures.py
"""
from __future__ import annotations

import html
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.demo_config import EPISODES, FEEDS, EpisodeSpec, FeedSpec  # noqa: E402

TZ8 = timezone(timedelta(hours=8))
OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


def _duration_hhmmss(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _pub_date(spec: EpisodeSpec) -> str:
    moment = datetime(spec.published_on.year, spec.published_on.month, spec.published_on.day, 9, 0, tzinfo=TZ8)
    return moment.strftime("%a, %d %b %Y %H:%M:%S %z")


def _feed_episodes(feed: FeedSpec) -> list[EpisodeSpec]:
    return [episode for episode in EPISODES if episode.feed_code == feed.code]


def _fixture_summary(episode: EpisodeSpec) -> str:
    return episode.summary_new


def build_rss(feed: FeedSpec) -> str:
    items: list[str] = []
    for episode in _feed_episodes(feed):
        items.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <title>{html.escape(episode.title)}</title>",
                    f'      <guid isPermaLink="false">{episode.guid}</guid>',
                    f"      <pubDate>{_pub_date(episode)}</pubDate>",
                    f"      <itunes:duration>{_duration_hhmmss(episode.duration_seconds)}</itunes:duration>",
                    f"      <itunes:season>{episode.season}</itunes:season>",
                    f"      <itunes:episode>{episode.episode_no}</itunes:episode>",
                    f"      <itunes:summary><![CDATA[{_fixture_summary(episode)}]]></itunes:summary>",
                    f"      <description><![CDATA[{episode.show_notes}]]></description>",
                    "    </item>",
                ]
            )
        )
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">',
            "  <channel>",
            f"    <title>{html.escape(feed.show_name)}</title>",
            f"    <link>{feed.url}</link>",
            f"    <description>{html.escape(feed.note)}</description>",
            "    <language>zh-cn</language>",
            f"    <lastBuildDate>{datetime(2026, 11, 12, 9, 0, tzinfo=TZ8).strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>",
            *items,
            "  </channel>",
            "</rss>",
            "",
        ]
    )


def build_platform(feed: FeedSpec) -> str:
    payload = {
        "show": {"code": feed.code, "name": feed.show_name, "host": feed.host},
        "endpoint": feed.url,
        "snapshot_at": "2026-11-12T09:00:00+08:00",
        "episodes": [
            {
                "id": episode.guid,
                "title": episode.title,
                "duration_seconds": episode.duration_seconds,
                "published_on": episode.published_on.isoformat(),
                "season": episode.season,
                "episode_no": episode.episode_no,
                "summary": _fixture_summary(episode),
                "notes": episode.show_notes,
            }
            for episode in _feed_episodes(feed)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_catalog(feed: FeedSpec) -> str:
    articles: list[str] = []
    for episode in _feed_episodes(feed):
        articles.append(
            "\n".join(
                [
                    (
                        f'    <article class="episode" data-guid="{episode.guid}" '
                        f'data-title="{html.escape(episode.title)}" '
                        f'data-duration="{episode.duration_seconds}" '
                        f'data-published="{episode.published_on.isoformat()}" '
                        f'data-summary="{html.escape(_fixture_summary(episode))}">'
                    ),
                    f"      <h2>{html.escape(episode.title)}</h2>",
                    f'      <pre class="show-notes">{html.escape(episode.show_notes)}</pre>',
                    "    </article>",
                ]
            )
        )
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "  <head>",
            '    <meta charset="utf-8" />',
            f"    <title>{html.escape(feed.show_name)} · 目录快照</title>",
            "  </head>",
            "  <body>",
            f'    <section class="catalog" data-show="{feed.code}" data-snapshot="2026-11-12T09:00:00+08:00">',
            f"      <h1>{html.escape(feed.show_name)}</h1>",
            *articles,
            "    </section>",
            "  </body>",
            "</html>",
            "",
        ]
    )


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for feed in FEEDS:
        if feed.kind == "rss":
            content = build_rss(feed)
        elif feed.kind == "platform":
            content = build_platform(feed)
        else:
            content = build_catalog(feed)
        path = OUT_DIR / feed.fixture_file
        path.write_text(content, encoding="utf-8")
        count = len(_feed_episodes(feed))
        total += count
        print(f"wrote {path.name:<16} kind={feed.kind:<8} episodes={count}")
    print(f"total episodes in fixtures = {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
