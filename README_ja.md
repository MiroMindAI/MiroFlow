<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_logo.png" width="45%" alt="MiroFlow" />
</div>

<br> 

<div align="center">

[![ドキュメント](https://img.shields.io/badge/Documentation-4285F4?style=for-the-badge&logo=gitbook&logoColor=white)](https://miromindai.github.io/MiroFlow/)
[![デモ](https://img.shields.io/badge/Demo-FFB300?style=for-the-badge&logo=airplayvideo&logoColor=white)](https://dr.miromind.ai/)
[![モデル](https://img.shields.io/badge/Models-5EDDD2?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/collections/miromind-ai/mirothinker-v02-68af084a18035f57b17cd902)
[![データ](https://img.shields.io/badge/Data-0040A1?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)

[![GITHUB](https://img.shields.io/badge/Github-24292F?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MiroMindAI)
[![ウェブサイト](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://miromind.ai/)
[![DISCORD](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/GPqEnkzQZd)
[![WeChat](https://img.shields.io/badge/WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white)](https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/assets/wechat.png)
[![RedNote](https://img.shields.io/badge/RedNote-FF2442?style=for-the-badge&logo=revoltdotchat&logoColor=white)](https://www.xiaohongshu.com/user/profile/5e353bd80000000001000239)

</div>

<div align="center">

### 🚀 [Try our Demo!](https://dr.miromind.ai/)｜[English](README.md)｜[中文](README_zh.md)

</div>

<div align="center">
  <img width="100%" alt="image" src="docs/mkdocs/docs/assets/futurex-09-12.png" />
</div>

---

このリポジトリは、MiroMind のリサーチエージェント・プロジェクトの**公式オープンソース**です。複雑な課題（例：将来イベントの予測）を解くために、インターネット深層リサーチを**マルチステップ**で実行できる、**高性能・完全オープンソース**の研究エージェント・システムです。現在、4つのコアコンポーネントを含みます：

* 🤖 **MiroFlow**：オープンソースの研究エージェント・フレームワーク。FutureX、GAIA、HLE、xBench-DeepSearch、BrowserComp など代表的ベンチマークで**再現可能な SOTA 性能**を達成（実装は本リポジトリ）。まずは [[5分でクイックスタート]](#-5分でクイックスタート) をお試しください。
* 🤔 **MiroThinker**：ツール支援推論をネイティブにサポートする、オープンソースのエージェント基盤モデル。詳細は [MiroThinker](https://github.com/MiroMindAI/mirothinker)。
* 📊 **MiroVerse**：研究エージェントの学習に使える**14.7万件の高品質データ**を公開。詳細は [MiroVerse](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)。
* 🚧 **MiroTrain / MiroRL**：研究エージェント・モデルを**安定かつ効率的に学習**させるためのインフラ。詳細は [MiroTrain](https://github.com/MiroMindAI/MiroTrain) / [MiroRL](https://github.com/MiroMindAI/MiroRL)。

---

## 📋 目次

* 📰 [最近の更新](#-最近の更新)
* 🚀 [5分でクイックスタート](#-5分でクイックスタート)
* 🤖 [MiroFlow とは？](#-miroflow-とは)
* 🌟 [主な特長](#-主な特長)
* ✨ [ベンチマーク性能](#-ベンチマーク性能)
* 🔧 [対応モデルとツール](#-対応モデルとツール)
* ❓ [FAQ](#-faq)
* 🤝 [コントリビュート](#-コントリビュート)
* 📄 [ライセンス](#-ライセンス)
* 🙏 [謝辞](#-謝辞)

---

## 📰 最近の更新

* **[2025-09-15]**: 🎉🎉 **MiroFlow v0.3**：リポジトリ構成を簡素化し、ベンチマーク性能を向上。GPT-5 の将来予測精度を **11% 向上**。FutureX の将来予測ベンチマークで**首位**に。詳細は [FutureX](https://futurex-ai.github.io/) を参照。
* **[2025-08-27]**: **MiroFlow v0.2**：複数の主要エージェント・ベンチマークで**最高性能**を達成。HLE (27.2%)、HLE-Text-Only (29.5%)、BrowserComp-EN (33.2%)、BrowserComp-ZH (47.1%)、xBench-DeepSearch (72.0%) などを**本リポジトリのコードで再現可能**。
* **[2025-08-26]**: [GAIA 検証トレース](docs/public_trace.md) (73.94% pass@1) と、ローカル展開用の [Gradio デモ](https://github.com/MiroMindAI/MiroThinker/tree/main/apps/gradio-demo) を公開。
* **[2025-08-08]**: **MiroFlow v0.1**：研究エージェント・フレームワークを**初めて完全公開**。

---

## 🚀 5分でクイックスタート

### 📋 事前準備

* **Python**: 3.12 以上
* **パッケージマネージャ**: [`uv`](https://docs.astral.sh/uv/)
* **OS**: Linux / macOS

## ⚡ クイックセットアップ

**例**: ドキュメント処理ツールを使った「インテリジェント文書分析」。

```bash
# 1. クローン & セットアップ
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. API キーを設定
cp .env.template .env
# .env を編集して OPENROUTER_API_KEY を追加

# 3. 最初のエージェントを実行
uv run main.py trace --config_file_name=agent_quickstart_reading --task="What is the first country listed in the XLSX file that have names starting with Co?" --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

🎉 **想定出力**: エージェントは **\boxed{Congo Democratic Republic}** を返すはずです 😊

> **💡 ヒント**: うまく動かない場合は、`.env` に API キーが正しく設定されているか、依存関係がすべてインストールされているかをご確認ください。

---

## 🤖 MiroFlow とは？

MiroFlow は、複雑な推論課題（例：将来イベント予測）で**最先端性能**を実現する、**高性能・モジュール型**の研究エージェント・フレームワークです。マルチラウンド対話、豊富なツール群の高度統合、階層型サブエージェントのスケジューリングに対応し、**タスク達成を最適化**します。詳しくは [フレームワーク概要](https://miromindai.github.io/MiroFlow/core_concepts/) をご覧ください。

<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_architecture.png" width="100%" alt="MiroFlow Architecture">
</div>

<table align="center" style="border: 1px solid #ccc; border-radius: 8px; padding: 12px; background-color: #f9f9f9; width: 60%;">
  <tr>
    <td style="text-align: center; padding: 10px;">
      <strong>Research Assistant Demo</strong> - 
      <span style="font-size: 0.9em; color: #555;">阅读CVPR 2025最佳论文并给出研究方向建议</span>
      <br>
      <video src="https://github.com/user-attachments/assets/99ed3172-6e9a-467a-9ccb-be45957fe2e4"
             controls muted preload="metadata"
             width="50%" height="50%"
      </video>
    </td>
  </tr>
</table>

---

## 🌟 主な特長

* **再現可能な SOTA 性能**：FutureX、GAIA、HLE、xBench-DeepSearch、BrowserComp などの[主要ベンチマーク](https://miromindai.github.io/MiroFlow/evaluation_overview/)で**首位**。
* **高い並行性と信頼性**：堅牢な並行処理とフォールトトレランス設計により、**レート制限のある API** や**不安定なネットワーク**下でも、データ収集と複雑タスクを**効率的かつ安定**して実行。
* **高コスパなデプロイ**：オープンソースの MiroThinker を基盤に、**単一の RTX 4090** でも研究エージェント・サービスを運用可能。スタックは**無料の OSS** に依存し、**デプロイ・拡張・再現**が容易。詳細は [MiroThinker](https://github.com/MiroMindAI/mirothinker)。

---

## 🔧 対応モデルとツール

* **モデル**: GPT / Claude / Gemini / Qwen / MiroThinker
* **ツール**: [音声転写](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/audio_mcp_server.py)、[Python](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/python_server.py)、[ファイル閲覧](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/reading_mcp_server.py)、[推論](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/reasoning_mcp_server.py)、[Google 検索](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/searching_mcp_server.py)、[ビジョンQA](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/vision_mcp_server.py)、E2B サンドボックス

---

## ✨ ベンチマーク性能

**2025年9月10日**時点で、MiroFlow は **FutureX リーダーボード**で**1位**、GPT-5 の将来予測精度を **11% 向上**。

<div align="center">
  <img width="100%" alt="image" src="docs/mkdocs/docs/assets/futurex-09-12.png" />
</div>

GAIA、HLE、BrowseComp、xBench-DeepSearch など**複数ベンチマーク**で評価し、**現時点で最良の結果**を獲得。

<img width="100%" alt="image" src="docs/mkdocs/docs/assets/benchmark_results.png" />

| モデル / フレームワーク        | GAIA Val  | HLE       | HLE-Text  | BrowserComp-EN | BrowserComp-ZH | xBench-DeepSearch |
| -------------------- | --------- | --------- | --------- | -------------- | -------------- | ----------------- |
| **MiroFlow**         | **82.4%** | **27.2%** | 29.5%     | 33.2%          | **47.1%**      | **72.0%**         |
| OpenAI Deep Research | 67.4%     | 26.6%     | -         | **51.5%**      | 42.9%          | -                 |
| Gemini Deep Research | -         | 26.9%     | -         | -              | -              | 50+%              |
| Kimi Researcher      | -         | -         | 26.9%     | -              | -              | 69.0%             |
| WebSailor-72B        | 55.4%     | -         | -         | -              | 30.1%          | 55.0%             |
| Manus                | 73.3%     | -         | -         | -              | -              | -                 |
| DeepSeek v3.1        | -         | -         | **29.8%** | -              | -              | 71.2%             |

再現方法は [ベンチマーク手順](https://miromindai.github.io/MiroFlow/evaluation_overview/) を参照してください。

---

## ❓ FAQ

<details>
<summary><strong>どの API キーが必要ですか？</strong></summary>
<br>
開始するには OpenRouter の API キーが 1 つあれば十分です。OpenRouter は単一の API を通じて複数の言語モデルへのアクセスを提供します。
</details>

<details>
<summary><strong>OpenRouter 以外の言語モデルも使用できますか？</strong></summary>
<br>
はい。MiroFlow はさまざまな言語モデルをサポートしています。設定の詳細はドキュメントをご覧ください。
</details>

<details>
<summary><strong>ベンチマーク結果を再現するにはどうすればよいですか？</strong></summary>
<br>
詳細な<a href="https://miromindai.github.io/MiroFlow/evaluation_overview/">ベンチマークドキュメント</a>に従って、ステップバイステップの再現ガイドをご確認ください。
</details>

<details>
<summary><strong>商用サポートはありますか？</strong></summary>
<br>
商用のご相談やエンタープライズ向けサポートが必要な方は、<a href="https://miromind.ai/">公式サイト</a>からお問い合わせください。
</details>

---

## 🤝 コントリビュート

コミュニティからの貢献を歓迎します！バグ修正、機能追加、ドキュメント改善など、あらゆる協力をお待ちしています。

- 📋 **Issue**: バグ報告・機能要望は [GitHub Issues](https://github.com/MiroMindAI/MiroFlow/issues) へ。
- 🔀 **Pull Request**: 改善はプルリクエストで送ってください。
- 💬 **ディスカッション**: 質問や議論は [Discord コミュニティ](https://discord.com/invite/GPqEnkzQZd) へ。

## 📄 ライセンス

本プロジェクトは **Apache License 2.0** の下で提供されています。

## 🙏 謝辞

- **ベンチマーク貢献者**：総合的な評価データセットの提供に感謝します。
- **OSS コミュニティ**：本プロジェクトを支えるツールとライブラリに感謝します。

MiroFlow の発展に貢献してくださったすべての方に感謝します：

<a href="https://github.com/MiroMindAI/MiroFlow/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MiroMindAI/MiroFlow" />
</a>

ぜひコミュニティに参加し、AI エージェントの未来を一緒に築きましょう！

## 参考文献

技術レポートは近日公開予定です！

```
@misc{2025mirothinker,
    title={MiroFlow: A High-Performance Open-Source Research Agent Framework},
    author={MiroMind AI Team},
    howpublished={\url{https://github.com/MiroMindAI/MiroFlow}},
    year={2025}
}
```

[![Star History Chart](https://api.star-history.com/svg?repos=MiroMindAI/MiroFlow&type=Date)](https://star-history.com/#MiroMindAI/MiroFlow&Date)
