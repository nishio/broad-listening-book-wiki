#!/usr/bin/env python3
"""
wiki/ → content/ へコピーしつつ、[[wikilink]] を Quartz が解決できるパスに変換する。

処理:
1. wiki/ 配下の全 .md ファイルをスキャンし、title と aliases から名前→パスの対応表を構築
2. 全ファイルを content/ にコピーしつつ、[[リンク名]] を [[相対パス|リンク名]] に変換
3. 対応するページが存在しないリンクはそのまま残す（プレーンテキスト化）

wiki/ のファイルはシンプルな [[ページ名]] で書けばよく、
パス解決はこのスクリプトが自動で行う。
"""

import os
import re
import shutil
import yaml

WIKI_DIR = os.path.join(os.path.dirname(__file__), '..', 'wiki')
CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content')

WIKI_DIR = os.path.abspath(WIKI_DIR)
CONTENT_DIR = os.path.abspath(CONTENT_DIR)


def extract_frontmatter(filepath):
    """ファイルからYAMLフロントマターを抽出"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if not content.startswith('---'):
        return {}, content
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, content


def build_link_map(wiki_dir):
    """
    名前 → 相対パス（拡張子なし）の対応表を構築。

    以下の名前でマッチする:
    - ファイル名（拡張子なし）: e.g. "kouchou-ai" → "entities/kouchou-ai"
    - title: e.g. "広聴AI" → "entities/kouchou-ai"
    - aliases の各エントリ: e.g. "広聴AI" → "entities/kouchou-ai"
    """
    link_map = {}

    for root, dirs, files in os.walk(wiki_dir):
        for fname in files:
            if not fname.endswith('.md'):
                continue

            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, wiki_dir)
            # 拡張子を除去し、パス区切りを / に統一
            slug = rel_path.replace(os.sep, '/').removesuffix('.md')

            # ファイル名（拡張子なし）
            basename = fname.removesuffix('.md')
            link_map[basename] = slug

            # フロントマターから title と aliases を取得
            fm, _ = extract_frontmatter(filepath)

            if fm.get('title'):
                link_map[fm['title']] = slug

            for alias in (fm.get('aliases') or []):
                link_map[alias] = slug

    return link_map


def resolve_wikilinks(content, link_map, current_slug):
    """
    [[リンク名]] → [[解決済みパス|リンク名]] に変換。
    [[パス|表示名]] 形式は既に解決済みとしてスキップ。
    """
    def replace_link(match):
        inner = match.group(1)

        # 既に [[path|display]] 形式の場合
        if '|' in inner:
            path_part, display = inner.split('|', 1)
            # path_part がlink_mapにある場合はパスに変換
            if path_part in link_map:
                resolved = link_map[path_part]
                return f'[[{resolved}|{display}]]'
            # path_part が既にパスっぽい場合はそのまま
            return match.group(0)

        # [[リンク名]] 形式
        link_name = inner.strip()

        if link_name in link_map:
            resolved = link_map[link_name]
            # 自分自身へのリンクはそのまま
            if resolved == current_slug:
                return f'**{link_name}**'
            # 表示名がファイル名と同じならパスだけでOK
            if link_name == resolved.split('/')[-1]:
                return f'[[{resolved}]]'
            return f'[[{resolved}|{link_name}]]'

        # 対応するページがない場合はプレーンテキストに
        return link_name

    return re.sub(r'\[\[([^\]]+)\]\]', replace_link, content)


def main():
    # link_map を構築
    link_map = build_link_map(WIKI_DIR)

    print(f"Link map ({len(link_map)} entries):")
    for name, slug in sorted(link_map.items()):
        print(f"  {name} → {slug}")
    print()

    # content/ をクリーンアップ
    if os.path.exists(CONTENT_DIR):
        shutil.rmtree(CONTENT_DIR)
    os.makedirs(CONTENT_DIR, exist_ok=True)

    # wiki/ → content/ にコピーしつつリンク解決
    file_count = 0

    for root, dirs, files in os.walk(WIKI_DIR):
        for fname in files:
            src = os.path.join(root, fname)
            rel = os.path.relpath(src, WIKI_DIR)
            dst = os.path.join(CONTENT_DIR, rel)

            os.makedirs(os.path.dirname(dst), exist_ok=True)

            if fname.endswith('.md'):
                with open(src, 'r', encoding='utf-8') as f:
                    content = f.read()

                slug = rel.replace(os.sep, '/').removesuffix('.md')
                new_content = resolve_wikilinks(content, link_map, slug)

                with open(dst, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                file_count += 1
            else:
                shutil.copy2(src, dst)

    print(f"Processed {file_count} markdown files")
    print(f"Output: {CONTENT_DIR}")

    # 検証: content/ 内の未解決リンク（対応するファイルが存在しないもの）を報告
    print("\nValidation - checking for broken links:")
    broken = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            filepath = os.path.join(root, fname)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            for m in re.finditer(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text):
                link_target = m.group(1)
                target_path = os.path.join(CONTENT_DIR, link_target + '.md')
                if not os.path.exists(target_path):
                    rel_file = os.path.relpath(filepath, CONTENT_DIR)
                    broken.append((rel_file, link_target))

    if broken:
        print(f"  WARNING: {len(broken)} broken link(s) found:")
        for src_file, target in broken:
            print(f"    {src_file} → [[{target}]]")
    else:
        print("  All links valid!")


if __name__ == '__main__':
    main()
