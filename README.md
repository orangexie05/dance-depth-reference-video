# Dance Depth Reference Video

这个 Skill 用于把一段用户有权使用的舞蹈或手势视频，转换为卡通或风格化角色的动作参考。核心链路是：

```text
源视频 -> 深度图或姿态骨架 -> 角色图/场景图 + 动作参考 -> 本地 payload -> 用户授权的生成 -> QA
```

项目提供本地视频检查、深度参考生成、姿态骨架生成和 MaybeAI/Seedance 参考 payload 构建脚本。它不上传媒体，也不替用户调用外部视频生成服务。

## Purpose and Non-goals

适用场景：保留源视频的动作顺序、节奏、转身、重心变化或关节轨迹，同时使用新的角色外观和场景生成视频。

不做以下事情：

- 不把黑白滤镜或简单去饱和当作深度图；深度参考必须来自深度估计模型。
- 不把深度图描述成显式关节/关键点轨迹；需要精确关节控制时使用单独的骨架分支。
- 不猜测或伪造 `local-doubao`、`api`、`maybeai`、`fal` 的 endpoint、模型或能力。
- 不把本地路径直接塞入外部 API 的 URL 字段，不替用户上传媒体。
- 不在未获授权时提交付费或外部生成请求，不并发提交多个镜头。

## Workflow

### 1. 检查源视频

先对下载到本地、且可合法处理的副本运行 `ffprobe` 封装脚本，记录时长、FPS、帧数、尺寸、编码、文件大小和音频状态：

```bash
python3 scripts/inspect_video.py /absolute/path/source.mp4
```

FPS 缺失、可变或文件不可读时先修复或确认是否允许规范化。不要自动裁剪、循环、加速、减速或补帧。超过所选 provider 的时长限制时，先由用户决定是否分段、换 provider 或换源视频。

### 2. 生成动作参考

深度分支使用真实的深度估计模型，脚本会保留源 FPS、尺寸、帧序和近似时长（误差不超过一帧）：

```bash
python3 scripts/make_depth_video.py \
  /absolute/path/source.mp4 /absolute/path/depth.mp4 \
  --model-id depth-anything/Depth-Anything-V2-Small-hf \
  --device auto
```

缺少运行时依赖时，脚本会明确报错；不要回退为灰度转换。可用 `--check-only` 只检查源视频元数据。Apple Silicon 可在适用时选择支持 MPS 的 PyTorch 构建。

需要明确关节路径、肢体角度、动作顺序或隔离外观时，使用 MediaPipe 骨架分支：

```bash
python3 scripts/make_skeleton_video.py \
  /absolute/path/source.mp4 /absolute/path/skeleton.mp4 \
  --json-output /absolute/path/skeleton.json
```

检查输出中的 `detection_rate`，并审阅手腕、脚踝、交叉肢体和脚部接触。检测率低或追踪不稳定时，修复追踪、处理镜头运动，或改用深度分支。

## Depth or Skeleton?

深度“看空间”：更适合身体体积、前后关系、转身、遮挡和重心转移，但不会显式识别关节，手指/手腕可能不精确。骨架“看关节”：更适合关键点路径、肢体角度和动作顺序，但会丢失体积、服装运动和部分 3D 遮挡。

选择规则：

1. provider 有明确的 pose/keypoint 控制字段时，优先骨架。
2. provider 有明确的 depth 控制字段时，优先深度。
3. 只有 generic reference-video 字段时，不宣称它必然解码为深度或骨架控制；先做短片 A/B 测试。全身风格化默认先测深度，再以骨架作为关节精度对照。
4. 除非 provider 明确支持独立多视频 conditioning，否则不要把深度和骨架同时塞入一个请求；分别提交 A/B job，避免两个无标签动作源冲突。

### 4. 准备角色与场景

角色图只负责角色外观、体型、服装和身份一致性；可选场景图只负责背景、空间布局、灯光和构图。不要让场景图变成第二个角色。若用户要求纯白背景，同时提供了场景图，先指出冲突再决定是否使用场景图。

### 5. 在本地构建 payload

`build_maybeai_payload.py` 只在本地生成带角色标签的 JSON；它不会上传文件、排队或生成视频。URL 参数必须是 HTTP(S) 或受支持的 Data URI；使用 `--*-file` 时脚本会把获准的本地文件编码为 Data URI。

```bash
python3 scripts/build_maybeai_payload.py \
  --character-file /absolute/path/character.png \
  --scene-file /absolute/path/scene.png \
  --motion-video-file /absolute/path/depth.mp4 \
  --motion-duration-seconds 5 \
  --duration 5 \
  --aspect-ratio 9:16 \
  --task-id depth-segment-01 \
  --output /absolute/path/maybeai-payload.json
```

脚本会拒绝超过 15 秒且未分段的动作参考，并校验整数时长和宽高比。对于超过 15 秒的源视频，先制作有标签的片段；记录每段源起点、源时长、请求的整数模型时长和后续拼接裁剪计划，不要静默补齐、循环或改速。

如需验证 MaybeAI 原生 function-call envelope，可在本地运行已安装 Skill 的校验脚本；这一步仍不是生成：

```bash
node /absolute/path/to/maybeai-video-function-call/scripts/fal_seedance.mjs \
  call_tool /absolute/path/maybeai-payload.json --pretty
```

只有用户明确授权后，才可将已确认的 payload 交给选定 provider 的生成入口。payload 构建与外部生成是两个独立步骤。

### 6. 选择 provider 并生成

分别选择 `image_provider` 和 `video_provider`，先读取 [references/provider-routing.md](references/provider-routing.md) 并探测能力：`image_reference`、`identity_lock`、`image_to_video`/`reference_video_to_video`、所选 motion 类型、depth/skeleton control、宽高比、时长、FPS、音频和结果下载。能力未知即视为未支持。

将 `max_in_flight` 固定为 `1`：提交一个镜头，等待完成，下载并检查后再继续。不得并行任务、并发重试，或在缺少运动控制时静默退化为 prompt-only 动画。

## Quick Start

下面的命令只处理本地文件或构建本地 JSON；不会发起视频生成请求。

```bash
# 读取源视频元数据
python3 scripts/inspect_video.py /absolute/path/source.mp4

# 使用深度估计模型生成时序保持的深度 MP4
python3 scripts/make_depth_video.py /absolute/path/source.mp4 /absolute/path/depth.mp4

# 使用 MediaPipe 生成时序保持的姿态骨架 MP4
python3 scripts/make_skeleton_video.py /absolute/path/source.mp4 /absolute/path/skeleton.mp4 --json-output /absolute/path/skeleton.json

# 生成带角色/场景/动作角色标签的 MaybeAI payload
python3 scripts/build_maybeai_payload.py --character-file /absolute/path/character.png --motion-video-file /absolute/path/depth.mp4 --duration 5 --aspect-ratio 9:16 --output /absolute/path/maybeai-payload.json
```

## Prerequisites and Installation

需要 Python 3、`ffmpeg`（包含 `ffprobe`）和可读写输入输出目录。按分支安装依赖：

```bash
# 深度分支
python3 -m pip install torch transformers pillow opencv-python numpy

# 骨架分支
python3 -m pip install mediapipe opencv-python numpy
```

建议在隔离的虚拟环境中安装。深度模型默认是 `depth-anything/Depth-Anything-V2-Small-hf`，首次运行可能需要下载模型。Node.js 仅在使用已安装的 MaybeAI function-call 校验脚本时需要。

## Authorization and Secret Handling

- 只处理用户拥有或明确获准转换、发布的源视频、角色图和场景图。
- 任何付费 fal.ai 请求前，展示最终 provider、payload 设置、参考视频时长和时长差异；收到明确授权后再提交。
- 生成器可读取已配置的 `FAL_AI_API_KEY` 或 `FAL_KEY`（以及 provider routing 中约定的适配器变量），但绝不打印、写入 README、payload、日志、测试快照或提交记录。
- 若环境只有 `FAL_AI_KEY`，可仅在当前命令环境映射为 `FAL_AI_API_KEY`；不要持久化或回显该值。
- 不把本地路径放入 API 的 `image_urls`/`video_urls` 等字段；先使用用户授权的媒体路由，或让 payload builder 生成 Data URI。这个 Skill 本身不上传媒体。

## Provider Constraints

详细 schema 见 [references/provider-constraints.md](references/provider-constraints.md)。以下限制必须在提交前检查：

### Seedance 2.0 Mini

- 模型：`bytedance/seedance-2.0/mini/reference-to-video`。
- 输入字段：`image_urls`、`video_urls`；使用 `@Image1`（角色）、可选 `@Image2`（场景）、`@Video1`（动作）。
- 参考视频总时长 2–15 秒，最多 3 个视频，合计小于 50 MB；输出 `duration` 为 `auto` 或 4–15 的整数秒。
- 支持 `720p` 等已记录设置和显式宽高比；`13.47` 秒无法由整数 `duration` 精确表达，必须向用户报告差异。

### Kling O3 Standard

- endpoint：`fal-ai/kling-video/o3/standard/reference-to-video`。
- 使用 `image_urls` 和 `elements[0].video_url`，动作 token 为 `@Element1`。
- 参考视频硬上限 10.05 秒；队列接受不代表结果一定成功，`video_duration_too_long` 时不要原样重试。
- 不要提交空 element、空图片字段或无关的结束图；骨架可替换深度做 A/B 测试，但不要无文档依据地同时提交两段动作视频。

### MiniMax H3 LoRA

- endpoint：`fal-ai/minimax_h3/reference-to-video/lora`。
- 使用 `reference_image_urls`、`reference_video_urls`、`loras`；角色/场景为图片 1/2，工作约定 token 为 `@图片1`、`@图片2`、`@视频1`。
- `duration` 为 5–15 的整数秒；`resolution` 为 `768P`、`2K` 或 `4K`；`aspect_ratio` 支持 `adaptive`、`21:9`、`16:9`、`4:3`、`1:1`、`3:4`、`9:16`。
- 每段参考视频 2–15 秒，合计不超过 15 秒；全部图片、视频、音频文件最多 12 个。请求固定比例时显式传入，不要用 `adaptive` 代替 `1:1`。
- 严格复刻动作时保持 `enable_prompt_expansion: false`，除非用户明确要求扩写。H3 的 schema 与 Seedance 的 `generate_audio` 不同；若用户要无声，生成后用 `ffmpeg -an` 去除音轨并重新 QA。

## QA Checklist

生成前检查：

- 源视频元数据可读，FPS/尺寸有效；深度输出来自模型，不是去饱和副本。
- 骨架 `detection_rate`、手腕/脚踝连续性、脚部接触和交叉肢体已人工抽查。
- 角色、场景、动作的输入字段和 prompt token 与 provider schema 一致；未使用的字段和空对象已删除。
- 参考视频时长、provider 上限、请求整数时长、比例和 `max_in_flight=1` 均已记录。

生成后用 `ffprobe` 或 `scripts/inspect_video.py` 检查实际 MP4：时长、尺寸、FPS、视频编码、音频状态和下载 URL。至少检查首帧、中段和末帧，确认：

- 脸、服装、比例和线稿/渲染风格稳定；无肢体扭曲、穿插、缺手缺脚或闪烁。
- 动作节奏、重心、转身、脚步和遮挡符合所选参考类型。
- 没有把源人物身份、脸、服装、背景、灯光、摄影风格、文字、logo 或水印带入结果。
- 场景构图遵循场景图；循环时首尾姿态可衔接。
- provider 返回的实际时长被如实报告；`duration` 只是目标值，不是 QA 证据。

## Failures and Layout

常见失败及处理：

- 黑白滤镜不是深度：安装依赖或选择模型，不能静默降级。
- Kling 超过 10.05 秒：改变源分段或 provider，不能只改输出 `duration`。
- 非整数源时长：报告 provider 无法精确表达的差异，不要隐藏或静默改速。
- 通用 reference-video 字段：在 A/B 测试确认前，只称为动作/风格参考，不称为深度或骨架控制。
- 骨架关键点缺失：修复追踪或改用深度分支。
- 输出跟随了角色图而不是 prompt 中写的角色名称：以实际参考图为准，重新确认角色资产。

项目布局保持 SkillHub/Codex 可识别的入口：

```text
SKILL.md                         主技能说明
agents/openai.yaml               Codex agent 元数据
scripts/                         四个本地处理与 payload 脚本
references/provider-*.md         provider 路由和约束
tests/                           布局与 payload 单元测试
```

## Safety and Rights

仅使用有权处理的源视频、角色素材、场景素材和 LoRA。对真人或受版权保护内容，确认必要的转换、发布和商业使用许可；不要通过提示词掩盖未经授权的身份或素材复制。外部生成前复核目标 provider、输入 URL、时长、费用和输出用途，并在用户明确授权后逐镜提交。

## Tests

在仓库根目录运行：

```bash
python3 -m unittest tests.test_skill_layout
python3 -m unittest discover -s tests -p 'test_*.py'
```

测试只验证布局、payload 字段和本地逻辑，不调用任何视频生成服务。
