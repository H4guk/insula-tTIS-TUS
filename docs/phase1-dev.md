# Phase 1 — tTIS のベース実装（dev）検証記録

対応 Issue: [#4](https://github.com/H4guk/insula-tTIS-TUS/issues/4)
目的: Yoon-sun + Montage I（T7–P7 / Fp1–Fp2）で tTIS 電場計算を**動く状態にする**（精度は Phase 2 / #7）。

このファイルは **工程を1つずつ検証した記録**。完成時に成果物としてまとめ直すための一次記録なので、
「何を確かめて / 何が分かって / 何が未確認か」を工程ごとに残す。

工程の一覧と現状は Issue #4 の工程表を参照（#1〜#9）。

---

## 工程1: モデルの用意（Yoon-sun 読込）

**確かめたこと**: エンティティが**閉じた立体（volume を持つ）**かどうか。
ボクセル化は「立体の内側を格子で塗る」処理なので、殻（面だけ）だと塗る内側が定義できず焼かれない。
ノートに「Skin は符号付き距離を返さない＝薄い殻」（2026-07-21）と「閉じたソリッド」（2026-07-29）の
**食い違った記録**が残っていたため、ここで確定させる必要があった。

**実行**（読み取りのみ）:

```python
import s4l_v1
import s4l_v1.model as model
import XCoreModeling as xc

cands = [n for n in dir(xc)
         if any(k in n.lower() for k in ('volume', 'closed', 'solid', 'watertight', 'valid', 'mass'))]
print('API 候補:', cands)

skin = [e for e in model.AllEntities() if e.Name == 'Skin'][0]
print('Skin 型:', type(skin).__name__)
for fn in cands:
    try:    print('  %-22s -> %s' % (fn, getattr(xc, fn)(skin)))
    except Exception as e: print('  %-22s -> 呼べない (%s)' % (fn, type(e).__name__))
```

**結果**（2026-07-31）:

| 項目 | 値 |
|---|---|
| `Skin` の型 | **`TriangleMesh`** |
| `xc.IsClosedSolidBody(skin)` | **False** |
| `xc.ConvertToSolid(skin)` | RuntimeError（引数不足・オプションが必要そう） |
| `xc.MeasureVolume(skin)` | TypeError（TriangleMesh には呼べない） |
| 全エンティティ数 | 330 |
| bbox | X 0–210.3 / Y 0–515.5 / Z 0–1661.2 mm（全身・足元原点） |

**判定: 工程1は原因ではない（✅ 読込は正常）**

理由:
1. `IsClosedSolidBody` は名前のとおり **`Body`（ソリッド）型を判定する API**。`TriangleMesh` に対する False は
   「型が Body でない」ことを言っているだけの可能性が高く、**メッシュが水密かどうかの判定にはなっていない**。
2. **決定的**: 箱テスト `BOXTEST_body` は `CreateSolidBlock` で作った**本物のソリッド Body** だが、
   **それも焼けなかった**。＝ **エンティティの型は焼ける/焼けないの分かれ目になっていない**。

**未確認として残すこと**:
- ViP メッシュが水密かどうか（`IsClosedSolidBody` では判定できていない）。
  ただし上記2により、これが工程7の主因である可能性は低い。
- `ConvertToSolid` は存在する。将来 ViP を Body 化する必要が出たら、この API のオプションを調べる。

**参照**: `Claude/Knowledge/sim4life-yoonsun-implementation.md` / `Claude/DailyLogs/2026-07-31.md`
