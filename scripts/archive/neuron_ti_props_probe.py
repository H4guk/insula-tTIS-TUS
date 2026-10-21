"""#16 L2 ③ の下調べ: Sim4Life の軸索の型で、直径・温度などを変えられるかを見る（Sim4Life.lite Python コンソール）。2026-10-16。

確かめること:
  - model に Sundt（無髄）の型があるか（名前に Neuron と Properties を含む関数の一覧）
  - MotorMrgNeuronProperties と Sundt の型が持つ設定の名前と既定値（直径・温度・節の数など）
MorphoSONIC 側は MRG 16 µm（7 節・間隔 1.500 mm・36 °C）と Sundt 0.8 µm（10 mm）なので、それに合わせられるかを見る。

結果（2026-10-16）:
  - 型の一覧に SundtNeuronProperties がある（ほかに Senn・Sweeney・SmallMrg・SensoryMrg・Tigerholm・Schild・Adelta など）
  - MotorMrg（既定 20 µm）: AxonDiameter 20.0・InternodeCount 6・NodeNodeSeparation 1759.16 µm・NodeDiameter 6.7496・
    MYSADiameter 6.8736・MYSALength 3.0・FLUTDiameter/STINDiameter 15.8696・FLUTLength 71.212・STINLength 268.29・
    NumberOfMyelinLamellae 164・NodeLength 1.0・周軸索腔 MYSA 0.002/FLUT・STIN 0.004（すべて ReadOnly False）
  - Sundt: AxonDiameter 0.8（MorphoSONIC で仮に置いた 0.8 µm と一致）・SectionLength 50.0 µm（MorphoSONIC は 21.9 µm）
  - 温度の設定は型の中に無い（ソルバー側の設定と見られる）
  比べると MorphoSONIC の MRG 20 µm（McIntyre 2002 の表）は nodeD 7.5・axonD 17.5・間隔 1700・FLUT 68・STIN 259.5・層 170 で、
  同じ 20 µm でも Sim4Life は形の数値が違う（直径からの式で出している可能性）。MorphoSONIC の 16 µm は
  nodeD 5.5・axonD 12.7・間隔 1500・MYSA 3.0・FLUT 60・STIN 228.83・層 150。
"""
import s4l_v1.model as model

print("[funcs]", [n for n in dir(model) if "Properties" in n])

def show(label, p):
    print("[%s] %s" % (label, type(p).__name__))
    for n in dir(p):
        if n.startswith("_"):
            continue
        try:
            v = getattr(p, n)
        except Exception as e:
            v = "<err %r>" % e
        if callable(v):
            continue
        print("   %-28s %r" % (n, v))

show("mrg", model.MotorMrgNeuronProperties())
for n in dir(model):
    if "Sundt" in n and "Properties" in n:
        show(n, getattr(model, n)())
