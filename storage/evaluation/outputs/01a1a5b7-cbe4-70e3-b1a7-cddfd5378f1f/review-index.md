# P2-Gold-01 候选审核索引

先按 B01–B12 查看首批证据，再在工作簿中以完整 candidate_id 记录逐条意见。索引行号对应工作簿初始排序，重新排序后请用 candidate_id 定位。

- [57 条人工审核表](review.xlsx)
- [首批 12 条证据包](first-batch-evidence.md)

## 本机校验记录

- P1 提交 `7810bfb54d43a1e5ffb4b6428bd30c0b4b0161a5`。生成清单记录的 5 个源文件哈希和提示词哈希均匹配，5 个源文件内容与该提交一致（比对时统一换行符）。
- 快照 `sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce`，schema v2。范围为 collection `default`、tenant `default`、permission_tags `["public"]`。
- 快照验证器核对清单与语料字节、记录一致性及权限，覆盖 3 份文档、447 个 Chunk。此处权限结论来自本地快照及引用记录。
- 快照清单内部哈希 `0ddcdfe183ab387767065dcf029dd31ba5cdf0088ee9dc7e3501254d72223827`，与生成清单的快照清单绑定值一致。
- 语料文件 SHA-256 `5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6`。
- 本次读取的生成清单文件 SHA-256 `f859cd0dc08dd2617f964887cb3994b1a7f1c2407a06423193ca49c0ed2d0581`。
- 57/57 条候选 ID 唯一且可重算，scope、snapshot_id 和 pending_review 一致。61 次引用指向 34 个现存 Chunk，引文逐字落在所引 Chunk 内。
- 全池为精确实体 23 条、语义检索 30 条、易混淆 4 条。首批按 5 / 5 / 2 选取并覆盖全部 3 份文档。原候选已通过机械完整性检查，问题适用性、答案是否完整和 PDF 解析保真度由人工判断。

| 生成清单登记的输出 | 复算 SHA-256 |
| --- | --- |
| `candidate_quality_report.json` | `cd304fcab441d28723e9b94b85c91e13ddb18698715d0d090e98d7cbea2b9711` |
| `candidates.jsonl` | `31df78af2c96afd25f9221034ab47bbd965f7cb1a5e182dc8c1560cc3f9cf120` |
| `coverage_gap_report.json` | `50fa7d7d6b05962f45c2400d935d34aefd0e71e9d64f7572d7bb0c1b6dd92374` |

## 审核顺序

| 工作簿行 | 首批编号 | candidate_id | 题型 | 快照证据位置 | 初始审核状态 |
| ---: | --- | --- | --- | --- | --- |
| 5 | [B01](first-batch-evidence.md#b01) | `sha256:9631dde730749e95e2c74da24726dd1d8e743b1242d189ac76034732a01fa5e9` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 29 | `pending_review` |
| 6 | [B02](first-batch-evidence.md#b02) | `sha256:6858125cbf5e8170a757c8a812aca9d1a9b2dd23347c59d5061af9a7c0d982f0` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 254 | `pending_review` |
| 7 | [B03](first-batch-evidence.md#b03) | `sha256:31d42a216450391763336ebbd7b38604cb50a3557831669e5b3371e63ef477ed` | 精确实体 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 1 | `pending_review` |
| 8 | [B04](first-batch-evidence.md#b04) | `sha256:4d263ebb839f347941da0bd9c9d0c11533925443e6a26519593ad7628f6c29e6` | 精确实体 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 19 | `pending_review` |
| 9 | [B05](first-batch-evidence.md#b05) | `sha256:e3783223e572063f0a3df106a6c1c6084c99e5f2943b788dc72a6996cb96b2bf` | 精确实体 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 25 | `pending_review` |
| 10 | [B06](first-batch-evidence.md#b06) | `sha256:bfd1eea2e2dfb6cd0dbda8053b95cae3aee6dc526998a08e1da1ee5458570a41` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 6 | `pending_review` |
| 11 | [B07](first-batch-evidence.md#b07) | `sha256:50354083653ee2bf6b5811362051fffcabfb7895978e5d6d0004c77ad21b0622` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 62 | `pending_review` |
| 12 | [B08](first-batch-evidence.md#b08) | `sha256:d5ab4e3c5473589238491da686184e9c651ecdbf317776b9454bc222b49ff81a` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 343 | `pending_review` |
| 13 | [B09](first-batch-evidence.md#b09) | `sha256:8d8e0f5cbd56fd6adb9ba5e09728cc911d24345d7a41f15ec0eaddc37717d1c8` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 58 | `pending_review` |
| 14 | [B10](first-batch-evidence.md#b10) | `sha256:b503d526e513f66d71916de151812a19403e51bbfd81956c88dee63adda7814a` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 280 | `pending_review` |
| 15 | [B11](first-batch-evidence.md#b11) | `sha256:de1dd6ecf011fd92f5cbef969545f045b067fbc353123e327f2b8ce04527a0d3` | 易混淆 | 电信基础设施维护规程.pdf · 快照页码 278 / 电信基础设施维护规程.pdf · 快照页码 277 | `pending_review` |
| 16 | [B12](first-batch-evidence.md#b12) | `sha256:70dc300fbcd568ccd4324dd4c6a93d6e438266da789c7865f0400d0c64547d24` | 易混淆 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 16 / 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 18 | `pending_review` |
| 17 | — | `sha256:ba50e7af3e31659d88a2d0b4937eb510a09e19e2238d1c0e93a923a1aa42fe50` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 10 | `pending_review` |
| 18 | — | `sha256:6b27f4cd6fb8a57d3ba3c96049bb0c8ce98b909be142ed809ab85a0bac89fba6` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 11 | `pending_review` |
| 19 | — | `sha256:029aaf51ce9894999917d4730c0682047e6aee33d34f15d1bbc64e1195361c91` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 12 | `pending_review` |
| 20 | — | `sha256:c0ee402dcbe543fe04df844c2c9d2134f4922a88177a166d82f0e2b2cdcd37c6` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 254 | `pending_review` |
| 21 | — | `sha256:8fcecc4204b0c7149f3d002b1b693d01b9be5a5e8930d621c5ef089f39e0585a` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 255 | `pending_review` |
| 22 | — | `sha256:b36c80cc90660614833ec0bdf464df7b4d37db9064457a2d1e2c496856ced6ba` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 255 | `pending_review` |
| 23 | — | `sha256:4f4129854aedf46810ac9654b5e918be591a55ffb3a8bd01c24ca7aa787237de` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 255 | `pending_review` |
| 24 | — | `sha256:0c141695e2654b721a2a70e712bfdd9cc951d132b823ef8b710b0f07c17d7f73` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 255 | `pending_review` |
| 25 | — | `sha256:af261cdb97be35e69dd294aff4351ed7ec7477048b2377adaee100697c1809d3` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 254 | `pending_review` |
| 26 | — | `sha256:474ea2ea4e472386215819df6edeb7f88ca3c1af3abae6259f11972588f52812` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 52 | `pending_review` |
| 27 | — | `sha256:0f3b338e277722ef4de67a59096d7e8c931138eb05c300808fc9d2ea9a186468` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 52 | `pending_review` |
| 28 | — | `sha256:d049bb19337a6de2e27a654729cdbfc8b84ef5e4b93dd4f31606dc51f4a0c6dd` | 精确实体 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 6 | `pending_review` |
| 29 | — | `sha256:2fa4c3c7182110647ed797c132138313300e447227199131a9731a8acd4a1afa` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 286 | `pending_review` |
| 30 | — | `sha256:6535e6f78dc8eeb10b933e995f8321cd01ed80d90f405c5042b7fbfccf08ac95` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 287 | `pending_review` |
| 31 | — | `sha256:0412887e0c24cae711a326d0032a59e8cce8c7618478be6748fd98c2cfc9f4bf` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 288 | `pending_review` |
| 32 | — | `sha256:9a72d01ef8f3b71904144877056fb2cf2f9ee7b02801140c14be922bb5fd8e9f` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 286 | `pending_review` |
| 33 | — | `sha256:2769ae9af89aab01bd8aead8897e96ebbe6e4f64ef305bcd59780fb192171860` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 287 | `pending_review` |
| 34 | — | `sha256:0691d0137cbe702a2ec0ed5fa33ab55628575d96781bf456d853a7d6d10191fe` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 61 | `pending_review` |
| 35 | — | `sha256:e74e6386379043f840835ab6571daade945ae870605a1d5f46da3dae7a977264` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 1 | `pending_review` |
| 36 | — | `sha256:86abb5904cd3b7241c6bd1baa9dc3888ec11fa28135c1fcb518ec9b19a51ddf1` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 2 | `pending_review` |
| 37 | — | `sha256:85516c936d8fe455b05be5cb507eabbdaf7aec41e0339101b9f7e34b688b65fc` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 2 | `pending_review` |
| 38 | — | `sha256:a9065f265727f73d5987f18a1b45172702509127e36212b003dfbcf857a24434` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 343 | `pending_review` |
| 39 | — | `sha256:64e18eda64f9eb7f2bea1fd707d05c637ed7e13c0bec0c586200017cd4e7c894` | 精确实体 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 3 | `pending_review` |
| 40 | — | `sha256:5d42c5b4ccd006231d17ae08a942cef1de654e37e64092884cae899a372110b4` | 精确实体 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 19 | `pending_review` |
| 41 | — | `sha256:7fe4ebfaf574ebd0825e8f2d4541c494239212b9c9f0c0dac94fb989a2eecf2d` | 语义检索 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 19 | `pending_review` |
| 42 | — | `sha256:2bbfb4a82fec1d093c88df135fb2f44eae2c0a27dcfd428bd8b7db7788180a76` | 易混淆 | 电信基础设施维护规程.pdf · 快照页码 278 / 电信基础设施维护规程.pdf · 快照页码 277 | `pending_review` |
| 43 | — | `sha256:d2bbc8a14069a7efff2b77ffee9522792c095fafbdfdad8ee4e8fa53a21a6f39` | 易混淆 | 电信基础设施维护规程.pdf · 快照页码 277 / 电信基础设施维护规程.pdf · 快照页码 279 | `pending_review` |
| 44 | — | `sha256:bc83c840f1e8d89aa0229f2e8e30c808cbad720e93970135313bb16204ef083c` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 277 | `pending_review` |
| 45 | — | `sha256:b4948d39941b4842ce1cec733083400393f944fb78b0a646fb187b3468ccfce5` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 278 | `pending_review` |
| 46 | — | `sha256:8b2d213a6a85dbee5975b9cc800f3c119222f1dd612bc93892999817cef85871` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 279 | `pending_review` |
| 47 | — | `sha256:e13b3e08b91f8ecc93a8f721859cde4e7d28675abb53ff5249a4334925abce47` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 278 | `pending_review` |
| 48 | — | `sha256:450131450e1fd2c9b087c8d9990ec5667dc54c25c979b4fb5929307174570c36` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 278 | `pending_review` |
| 49 | — | `sha256:de211868b35c7ce7c3fc759a17333f5829c97542cbfdafcadbb0445afc020266` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 279 | `pending_review` |
| 50 | — | `sha256:d3109d6f7c5c9e35cef41bc51a466b88a5710a071e90e19c393e7ec18be79879` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 279 | `pending_review` |
| 51 | — | `sha256:be11ad9c57042e53066edc836c22ea22c1df359c8f46d7bc09e5beca283fdef2` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 25 | `pending_review` |
| 52 | — | `sha256:1cb66bac6381fa7f068e3c89a5469e939babb508ee62c54f3b6ff24ee0272ca0` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 91 | `pending_review` |
| 53 | — | `sha256:b3cb46209708867debeabfffc91132b4d88fd613ee9017f7959edaa1a71a120f` | 精确实体 | 电信基础设施维护规程.pdf · 快照页码 92 | `pending_review` |
| 54 | — | `sha256:a20b570f5a28d69b3e7aebf3083c0cfe0b1913c34693320496fa4e5f345ac2e0` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 91 | `pending_review` |
| 55 | — | `sha256:7b3828d049462c38db624dc89d1733b296d18c8673d71242117f95c3413f7e8c` | 精确实体 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 58 | `pending_review` |
| 56 | — | `sha256:8d25da17cd828fdd5a472d80f1de41390f9e26616d31ff42715c6436e79fff2b` | 精确实体 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 60 | `pending_review` |
| 57 | — | `sha256:38376d247fabd496f655addd308a80ce91e133aa70c3d6108bb93404f33d0d2c` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 60 | `pending_review` |
| 58 | — | `sha256:1c41c10613d8867a8469f80d9d506a49a58357bcd7030fa9b1a07d4655c5386c` | 精确实体 | 智慧家庭装维工程与管理职业技能等级标准.pdf · 快照页码 14 | `pending_review` |
| 59 | — | `sha256:672fe784fc33b88b4fb7660dcda841815d3c30a876eb39164ce3909a9d765374` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 281 | `pending_review` |
| 60 | — | `sha256:5972f5480aeed3b4b705cc948d70c8ac5034cd30cb5c1ca0f9c2c08206a17c99` | 语义检索 | 电信基础设施维护规程.pdf · 快照页码 282 | `pending_review` |
| 61 | — | `sha256:75f444c4a8d849e38771a34c0a5ad510d8b399a5381829f102e7632eb272a392` | 语义检索 | 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf · 快照页码 64 | `pending_review` |
