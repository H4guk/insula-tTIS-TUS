"""#16 L2 ③ の下調べ 2: Sim4Life の MotorMrg の AxonDiameter を 16 にすると、ほかの形の数値も自動で変わるか（Sim4Life.lite Python コンソール）。2026-10-16。

MorphoSONIC の MRG 16 µm（McIntyre 2002 の表）: NodeDiameter 5.5・軸索の直径 12.7・節の間隔 1500・MYSA 3.0・FLUT 60・STIN 228.83・層 150。
自動で変わらない、または表と違う値になるなら、次のスクリプトでこの値を直接入れる。

結果（2026-10-16）: AxonDiameter を 16 にすると、ほかの形の数値も自動で変わる（直径からの式）。
  項目                 Sim4Life 16 µm   MorphoSONIC 16 µm（McIntyre 2002 の表）  差
  NodeNodeSeparation   1542.87          1500                                    +2.9%
  NodeDiameter         5.37             5.5                                     -2.4%
  MYSADiameter         5.4628           5.5（= 節の直径）                        -0.7%
  FLUT/STINDiameter    12.3136          12.7                                    -3.0%
  FLUTLength           60.8876          60                                      +1.5%
  STINLength           235.68           228.83（= (1500 - 1 - 2*3 - 2*60) / 6）  +3.0%
  NumberOfMyelinLamellae 150            150                                      0
  InternodeCount 6・NodeLength 1・MYSALength 3 は同じ。
"""
import s4l_v1.model as model

keys = ["AxonDiameter", "NodeNodeSeparation", "InternodeCount", "NodeDiameter", "NodeLength",
        "MYSADiameter", "MYSALength", "FLUTDiameter", "FLUTLength", "STINDiameter", "STINLength",
        "NumberOfMyelinLamellae"]

p = model.MotorMrgNeuronProperties()
before = dict((k, getattr(p, k)) for k in keys)
p.AxonDiameter = 16.0
for k in keys:
    print("%-24s %12.4f -> %12.4f" % (k, before[k], getattr(p, k)))
