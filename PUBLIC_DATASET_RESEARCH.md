# Public Face-Dataset Research

**Research date:** 2 November 2026
**Scope:** Research only. No dataset or model was downloaded, no account/access request was submitted, and no licence was accepted.

## Ranked recommendation

Use public data only for a defined research question. Public celebrity datasets do not replace consented employee enrolment or kiosk testing.

| Rank | Dataset | Official source and publication | Access / permission | Licence and commercial status | Scale, resolution, purpose | Storage/hardware | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [LFW](http://vis-www.cs.umass.edu/lfw/) | [UMass original paper](https://people.cs.umass.edu/~elm/papers/lfw.pdf) | No registration requirement was identified. Official archive: `http://vis-www.cs.umass.edu/lfw/lfw.tgz`; aligned archive: `http://vis-www.cs.umass.edu/lfw/lfw-funneled.tgz`. Review portal terms before download. | Research benchmark; commercial permission was not established in this research. | 13,233 images, 5,749 identities; original 250Ã—250 images; standard 6,000-pair verification protocol. | About 200 MB; CPU inference is sufficient. | Best first verification benchmark, conditional on terms review. |
| 2 | [CFP / CFP-FP](http://www.cfpw.io/) | [Official CFP project portal](http://www.cfpw.io/) | The official portal timed out during research. A direct archive, registration requirement, and live licence text could not be verified. | Unverifiedâ€”do not download or use commercially until confirmed with maintainers. | 500 identities, 7,000 images (10 frontal + 4 profile per identity); CFP-FP is a frontal/profile verification protocol. Official canonical resolution not verified. | Likely under 1 GB; CPU inference sufficient. | Good pose benchmark, but only after official access/terms check. |
| 3 | [CPLFW](http://www.whdeng.cn/CPLFW/) | [Original paper](https://www.whdeng.cn/CPLFW/Cross-Pose-LFW.pdf) | The paper names the official author portal, which was unreachable during research. Direct archive/registration/licence not verified. | Unverifiedâ€”do not download or use commercially until confirmed with maintainers. | 11,652 images, 3,930 identities; 6,000 verification pairs; designed for difficult cross-pose matching. | Likely under 1 GB; CPU inference sufficient. | Good complementary pose benchmark, conditional on terms verification. |
| 4 | [FairFace](https://github.com/joojs/fairface) | [WACV 2021 paper](https://openaccess.thecvf.com/content/WACV2021/papers/Karkkainen_FairFace_Face_Attribute_Dataset_for_Balanced_Race_Gender_and_Age_WACV_2021_paper.pdf) | Official repository links to Google Drive images/labels; no registration indicated. | Repository states CC BY 4.0; attribution required. Confirm each downloaded artefactâ€™s notice. | 108,501 images; age/gender/race attributes across 7 race groups; commonly distributed as 448Ã—448 crops. Not an identity-verification dataset. | Several GB; CPU preprocessing, modest GPU optional. | Optional for bias/attribute awarenessâ€”not identity recognition evaluation. |
| 5 | [CelebA](https://mmlab.ie.cuhk.edu.hk/projects/CelebA.html) | [ICCV 2015 paper](https://liuziwei7.github.io/projects/FaceAttributes.html) | Official downloads exist. Identity labels require a research request. | Non-commercial research only; no redistribution/commercial use. | 202,599 images, 10,177 identities, 178Ã—218 aligned crops; landmarks/attributes. | 1.34 GB aligned; about 9.8 GB original. | Optional learning resource only; do not use for portfolio deployment claims. |
| 6 | CASIA-WebFace | [Original paper](https://arxiv.org/abs/1411.7923) | Historical official URL: `http://www.cbsr.ia.ac.cn/english/CASIA-WebFace-Database.html`; no reliable active official download was verified. | Current terms and commercial permission unverified. Do not use mirrors. | About 0.5M images, about 10.5k identities; redistributed variants are often 112Ã—112 but that is not a canonical official release statement. | Tens of GB; large-training GPU workload. | Do not use: access/terms unresolved and training is out of scope. |
| 7 | VGGFace2 | [Oxford record](https://ora.ox.ac.uk/objects/uuid%3Aabe79fff-9d75-4a5d-a8ca-4ae3ffca6356) and [paper](https://www.robots.ox.ac.uk/~vgg/publications/2018/Cao18/cao18.pdf) | No current reliable official data download was verified. Do not use mirrors. | Current official terms unverified. | 3.31M images, 9,131 identities; designed for pose/age variation. | Commonly cited downloads: ~36 GB training + 1.9 GB test; GPU/disk intensive. | Do not use: unnecessary at this scale and official access is uncertain. |
| 8 | IJB-C | [NIST Face Challenges](https://www.nist.gov/programs-projects/face-challenges) | NIST challenge material and per-image source rights must be reviewed before access. | Mixed source licences; no blanket commercial grant. | Difficult still/video template verification/identification benchmark. | Multi-GB and complex; GPU beneficial. | Advanced option, not an initial student benchmark. |

## What each dataset can and cannot establish

- **LFW, CFP-FP, and CPLFW** measure 1:1 face verification using published pairs. They are useful for learning cosine-similarity thresholds and benchmark methodology, but do not validate open-set, 1:N employee identification at a kiosk.
- **FairFace and CelebA** are useful for attributes, alignment, image handling, and bias-awareness. They are not substitutes for identity recognition evaluation of attendance employees.
- **CASIA-WebFace and VGGFace2** are historical large-scale training data. They are not needed because this project will begin with pretrained embeddings rather than train a neural network from scratch.
- **A consented local dataset is mandatory** for employee enrolment, image-quality gates, unknown-person rejection, FAR/FRR, and the actual webcam/lighting/distance conditions.

## Pretrained model recommendation and separate licensing

For the educational portfolio phase, the recommended architecture is a replaceable **ArcFace-style embedding adapter**, initially evaluated with an InsightFace pretrained model: detect and align one face, create a normalized embedding, then use cosine similarity against consented enrolled templates. This demonstrates modern computer vision without training a large network.

[InsightFace](https://github.com/deepinsight/insightface) makes a crucial distinction: its **code** is MIT, while the public pretrained models/model packs and their training data are for **non-commercial research only**. Therefore, this is a research/portfolio recommendation, not permission for commercial or organisational deployment. Commercial use requires separate authorisation or a separately licensed model. Downloaded weights must never be committed to Git.

| Approach | Value | Decision |
| --- | --- | --- |
| Train from scratch | Teaches training infrastructure, but needs large lawful data and substantial GPUs. | Not practical for this project. |
| Pretrained ArcFace-style embeddings | Teaches detection, alignment, embeddings, cosine similarity, thresholds, FAR/FRR, and evaluation. | Recommended research starting point, subject to model-term approval. |
| Fine-tune pretrained model | Can be useful only with enough lawful, independent data and a measured need. | Defer; it is not needed for the initial portfolio system. |

## Concepts to explain

- **Detection** locates a face; **recognition** compares its representation with enrolled representations.
- An **embedding** is a fixed-length numerical face representation. **Cosine similarity** measures how closely two normalized embeddings point in the same direction; it is not an identity probability.
- A **threshold** accepts/rejects a comparison and must be fitted on validation data then checked on held-out data.
- **Known/unknown rejection** must refuse weak matches rather than label every face as the nearest enrolled person.
- **FAR** is impostor acceptance; **FRR** is genuine-person rejection. Both depend on operating conditions and threshold.
- **Inference speed** is measured latency/FPS on named hardware. Benchmark accuracy does not automatically transfer to a webcam attendance system.

## Approval gate

Before any download, choose a dataset, confirm its current official terms, state the intended non-commercial research use, allocate local storage outside Git, and approve the exact model/model-weight licence. For CFP-FP, CPLFW, CASIA-WebFace, VGGFace2, and IJB-C, live official access/licence verification is an additional required gate.
